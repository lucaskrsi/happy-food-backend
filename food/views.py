from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .permissions import IsAdminOrReadOnly, IsRestaurante, IsEntregador, IsCliente
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from .models import (
    Endereco, GrupoOpcao, Opcao, Usuario, Restaurante, CategoriaProduto, Produto,
    Carrinho, ItemCarrinho, Pedido, ItemPedido, Pagamento,
    Entrega, RastreamentoEntrega,
    AvaliacaoRestaurante, AvaliacaoEntregador, AvaliacaoProduto
)
from .serializers import (
    EnderecoSerializer, GrupoOpcaoSerializer, OpcaoSerializer, UsuarioSerializer, RestauranteSerializer,
    CategoriaProdutoSerializer, ProdutoSerializer,
    CarrinhoSerializer, ItemCarrinhoSerializer,
    PedidoSerializer, ItemPedidoSerializer, PagamentoSerializer,
    EntregaSerializer, RastreamentoEntregaSerializer,
    AvaliacaoRestauranteSerializer, AvaliacaoEntregadorSerializer, AvaliacaoProdutoSerializer
)

# -----------------------------
# USUÁRIOS
# -----------------------------

class GoogleLoginView(APIView):
    """
    Endpoint para login/cadastro via conta Google.
    Frontend deve enviar o id_token do Google.
    """
    def post(self, request):
        token = request.data.get("id_token")

        if not token:
            return Response({"erro": "Token Google ausente."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # valida o token
            info = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

            email = info.get("email")
            nome = info.get("name", "")
            foto_url = info.get("picture", "")

            if not email:
                return Response({"erro": "Token inválido: sem email."}, status=status.HTTP_400_BAD_REQUEST)

            # busca ou cria o usuário
            usuario, criado = Usuario.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": nome,
                    "foto": foto_url,  # opcional: pode salvar a URL da foto do Google
                    "ativo": True,
                },
            )

            # gera tokens JWT
            refresh = RefreshToken.for_user(usuario)

            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "usuario": {
                    "id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "foto": usuario.foto.url if usuario.foto else None,
                }
            })

        except ValueError:
            return Response({"erro": "Token Google inválido."}, status=status.HTTP_400_BAD_REQUEST)

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['post'], url_path='registrar')
    def registrar(self, request):
        """Endpoint para cadastrar novo cliente"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'mensagem': 'Usuário criado com sucesso!'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='atualizar_senha', url_name='atualizar_senha')
    def atualizar_senha(self, request, pk=None):
        """Atualiza a senha do usuário"""
        usuario = self.get_object()
        nova_senha = request.data.get("password")

        if not nova_senha:
            return Response({'erro': 'O campo "password" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(nova_senha)
        usuario.save()
        return Response({'mensagem': 'Senha atualizada com sucesso.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='foto', url_name='atualizar_foto')
    def atualizar_foto(self, request, pk=None):
        """Atualiza apenas a foto do usuário"""
        usuario = self.get_object()
        
        if 'foto' not in request.data:
            return Response(
                {'erro': 'O campo "foto" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario.foto = request.data['foto']
        usuario.save()
        serializer = self.get_serializer(usuario)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remover_foto(self, request, pk=None):
        """Remove a foto de perfil do usuário (define como None)."""
        usuario = self.get_object()

        if request.user != usuario and not request.user.is_staff:
            return Response({'erro': 'Permissão negada.'}, status=status.HTTP_403_FORBIDDEN)

        if usuario.foto:
            usuario.foto.delete(save=False)

        usuario.foto = None
        usuario.save()

        return Response({'mensagem': 'Foto de perfil removida com sucesso.'}, status=status.HTTP_200_OK)

# -----------------------------
# RESTAURANTES E PRODUTOS
# -----------------------------
class RestauranteViewSet(viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.perfil in ('cliente', 'entregador'):
            return Restaurante.objects.filter(aberto=True)
        
        if user.perfil == 'restaurante':
            return Restaurante.objects.filter(dono=user)

        if user.is_staff or user.is_superuser:
            return Restaurante.objects.all()
        
        return Restaurante.objects.all()
    
    def get_permissions(self):
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), IsRestaurante()]
        return [permissions.AllowAny(),]

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'perfil') or self.request.user.perfil != 'restaurante':
            raise PermissionDenied("Apenas usuários com perfil 'restaurante' podem criar restaurantes.")
        serializer.save(dono=self.request.user)

    @action(detail=True, methods=['get'])
    def produtos(self, request, pk=None):
        """Listar produtos de um restaurante específico"""
        restaurante = self.get_object()
        produtos = restaurante.produtos.all()
        serializer = ProdutoSerializer(produtos, many=True)
        return Response(serializer.data)
                      

class CategoriaProdutoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaProduto.objects.all()
    serializer_class = CategoriaProdutoSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        # só restaurantes (ou admin) podem criar/editar produtos
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), IsAdminOrReadOnly()]
        return [permissions.AllowAny(),]


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    def get_permissions(self):
        # só restaurantes (ou admin) podem criar/editar produtos
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return [IsAuthenticated(), IsRestaurante()]
        return [permissions.AllowAny(),]
    
    @action(detail=True, methods=['get'], url_path='grupos-opcoes', url_name='grupos_opcoes')
    def grupos_opcoes(self, request, pk=None):
        """Listar grupos de opções de um produto específico"""
        produto = self.get_object()
        grupos = produto.grupos_opcoes.all()
        serializer = GrupoOpcaoSerializer(grupos, many=True)
        return Response(serializer.data)

class GrupoOpcaoViewSet(viewsets.ModelViewSet):
    queryset = GrupoOpcao.objects.all()
    serializer_class = GrupoOpcaoSerializer
    permission_classes = [permissions.IsAuthenticated, IsRestaurante]

    @action(detail=True, methods=['get'])
    def opcoes(self, request, pk=None):
        """Listar opções de um grupo de opções específico"""
        grupo = self.get_object()
        opcoes = grupo.opcoes.all()
        serializer = OpcaoSerializer(opcoes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='adicionar', url_name='adicionar')
    def adicionar_opcao(self, request, pk=None):
        """Adicionar uma opção a um grupo de opções"""
        grupo = self.get_object()
        nome = request.data.get('nome')
        preco_adicional = request.data.get('preco_adicional', 0)

        if not nome:
            return Response({'erro': 'O campo "nome" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        opcao = Opcao.objects.create(grupo=grupo, nome=nome, preco_adicional=preco_adicional)
        # grupo.opcoes.add(opcao)
        # grupo.save()

        return Response(OpcaoSerializer(opcao).data, status=status.HTTP_201_CREATED)


# -----------------------------
# CARRINHO
# -----------------------------
class CarrinhoViewSet(viewsets.ModelViewSet):
    queryset = Carrinho.objects.all()
    serializer_class = CarrinhoSerializer
    permission_classes = [permissions.IsAuthenticated, IsCliente]

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        carrinho = self.get_object()
        itens_do_carrinho = carrinho.itens.all()
        if not itens_do_carrinho.exists():
            return Response({'erro': 'Carrinho vazio.'}, status=status.HTTP_400_BAD_REQUEST)
        
        restaurante = itens_do_carrinho.first().produto.restaurante

        #Endereço
        endereco_id = request.data.get('endereco_id')
        if not endereco_id:
            return Response({'erro': 'É necessário informar o endereço_id.'}, status=status.HTTP_400_BAD_REQUEST)

        endereco_cliente = get_object_or_404(Endereco, id=endereco_id, usuario=request.user)

        endereco_entrega = endereco_cliente.gerar_snapshot()
        
        if restaurante.enderecos.exists():
            endereco_origem = restaurante.enderecos.gerar_snapshot()
        else:
            endereco_origem = "Endereço do restaurante não cadastrado."

        try:
            with transaction.atomic():
                pedido = Pedido.objects.create(
                    usuario=carrinho.usuario,
                    restaurante=restaurante,
                    endereco_entrega=endereco_entrega,
                    endereco_origem=endereco_origem
                )
                for item_carrinho in itens_do_carrinho:
                    item_pedido = ItemPedido.from_item_carrinho(item_carrinho, pedido)
                    item_pedido.save()

                pedido.valor_total = sum(i.subtotal() for i in pedido.itens.all())
                pedido.save()

                pedido = finalizar_carrinho(carrinho)
                carrinho.itens.all().delete()
            serializer = PedidoSerializer(pedido)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def adicionar_item(self, request, pk=None):
        """Adiciona produto ao carrinho"""
        carrinho = self.get_object()
        produto_id = request.data.get('produto_id')
        quantidade = int(request.data.get('quantidade', 1))
        observacao = request.data.get('observacao', '')

        try:
            produto = Produto.objects.get(id=produto_id)
        except Produto.DoesNotExist:
            return Response({'erro': 'Produto não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        item, criado = ItemCarrinho.objects.get_or_create(
            carrinho=carrinho, produto=produto,
            defaults={'quantidade': quantidade, 'observacao': observacao}
        )

        if not criado:
            item.quantidade += quantidade
            item.save()

        return Response(ItemCarrinhoSerializer(item).data, status=status.HTTP_201_CREATED)


# -----------------------------
# PEDIDOS E PAGAMENTOS
# -----------------------------
class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated, IsCliente]

    @action(detail=True, methods=['post'])
    def alterar_status(self, request, pk=None):
        """Permite o restaurante ou admin mudar status do pedido"""
        pedido = self.get_object()
        novo_status = request.data.get('status')

        if novo_status not in dict(Pedido._meta.get_field('status').choices):
            return Response({'erro': 'Status inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        pedido.status = novo_status
        pedido.save()
        return Response(PedidoSerializer(pedido).data)

    @action(detail=True, methods=['get'])
    def pagamento(self, request, pk=None):
        """Retorna pagamento vinculado a um pedido"""
        pedido = self.get_object()
        if hasattr(pedido, 'pagamento'):
            return Response(PagamentoSerializer(pedido.pagamento).data)
        return Response({'mensagem': 'Sem pagamento registrado.'})


class PagamentoViewSet(viewsets.ModelViewSet):
    queryset = Pagamento.objects.all()
    serializer_class = PagamentoSerializer
    permission_classes = [permissions.IsAuthenticated]


# -----------------------------
# ENTREGA E RASTREAMENTO
# -----------------------------
class EntregaViewSet(viewsets.ModelViewSet):
    queryset = Entrega.objects.all()
    serializer_class = EntregaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def atualizar_localizacao(self, request, pk=None):
        """Entregador atualiza coordenadas GPS"""
        entrega = self.get_object()
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response({'erro': 'Latitude e longitude são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        rastreamento = RastreamentoEntrega.objects.create(
            entrega=entrega, latitude=latitude, longitude=longitude
        )
        return Response(RastreamentoEntregaSerializer(rastreamento).data, status=status.HTTP_201_CREATED)


# -----------------------------
# AVALIAÇÕES
# -----------------------------
class AvaliacaoRestauranteViewSet(viewsets.ModelViewSet):
    queryset = AvaliacaoRestaurante.objects.all()
    serializer_class = AvaliacaoRestauranteSerializer
    permission_classes = [permissions.IsAuthenticated]


class AvaliacaoEntregadorViewSet(viewsets.ModelViewSet):
    queryset = AvaliacaoEntregador.objects.all()
    serializer_class = AvaliacaoEntregadorSerializer
    permission_classes = [permissions.IsAuthenticated]


class AvaliacaoProdutoViewSet(viewsets.ModelViewSet):
    queryset = AvaliacaoProduto.objects.all()
    serializer_class = AvaliacaoProdutoSerializer
    permission_classes = [permissions.IsAuthenticated]

class EnderecoViewSet(viewsets.ModelViewSet):
    queryset = Endereco.objects.all()
    serializer_class = EnderecoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Endereco.objects.all()
        return Endereco.objects.filter(usuario=user)
    
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=['post'], url_path='vincular-restaurante', url_name='vincular-restaurante')
    def vincular_restaurante(self, request, pk=None):
        """Vincula um endereço a um restaurante"""
        endereco = self.get_object()
        restaurante_id = request.data.get('restaurante_id')

        try:
            restaurante = Restaurante.objects.get(id=restaurante_id)
        except Restaurante.DoesNotExist:
            return Response({'erro': 'Restaurante não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        endereco.restaurante = restaurante
        endereco.save()
        return Response(EnderecoSerializer(endereco).data)
    
    @action(detail=True, methods=['delete'], url_path='desvincular-restaurante', url_name='desvincular-restaurante')
    def desvincular_restaurante(self, request, pk=None):
        """Desvincula um endereço de um restaurante"""
        endereco = self.get_object()
        endereco.restaurante = None
        endereco.save()
        return Response(EnderecoSerializer(endereco).data)

    @action(detail=False, methods=['get'], url_path='enderecos-restaurante', url_name='enderecos-restaurante')
    def enderecos_restaurante(self, request):
        """Lista endereços vinculados a um restaurante específico"""
        restaurante_id = request.query_params.get('restaurante_id')

        try:
            restaurante = Restaurante.objects.get(id=restaurante_id)
        except Restaurante.DoesNotExist:
            return Response({'erro': 'Restaurante não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        enderecos = Endereco.objects.filter(restaurante=restaurante)
        serializer = EnderecoSerializer(enderecos, many=True)
        return Response(serializer.data)
