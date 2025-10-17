from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .permissions import IsRestaurante, IsEntregador
from rest_framework.permissions import IsAuthenticated
from .models import (
    Usuario, PerfilUsuario, Restaurante, CategoriaProduto, Produto,
    Carrinho, ItemCarrinho, Pedido, ItemPedido, Pagamento,
    Entrega, RastreamentoEntrega,
    AvaliacaoRestaurante, AvaliacaoEntregador, AvaliacaoProduto
)
from .serializers import (
    UsuarioSerializer, PerfilUsuarioSerializer, RestauranteSerializer,
    CategoriaProdutoSerializer, ProdutoSerializer,
    CarrinhoSerializer, ItemCarrinhoSerializer,
    PedidoSerializer, ItemPedidoSerializer, PagamentoSerializer,
    EntregaSerializer, RastreamentoEntregaSerializer,
    AvaliacaoRestauranteSerializer, AvaliacaoEntregadorSerializer, AvaliacaoProdutoSerializer
)

# -----------------------------
# USUÁRIOS
# -----------------------------
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'], url_path='registrar')
    def registrar(self, request):
        """Endpoint para cadastrar novo cliente"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'mensagem': 'Usuário cliente criado com sucesso!'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -----------------------------
# RESTAURANTES E PRODUTOS
# -----------------------------
class RestauranteViewSet(viewsets.ModelViewSet):
    queryset = Restaurante.objects.all()
    serializer_class = RestauranteSerializer
    permission_classes = [permissions.AllowAny]

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


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    def get_permissions(self):
        # só restaurantes (ou admin) podem criar/editar produtos
        if self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated(), IsRestaurante()]
        return [permissions.AllowAny(),]


# -----------------------------
# CARRINHO
# -----------------------------
class CarrinhoViewSet(viewsets.ModelViewSet):
    queryset = Carrinho.objects.all()
    serializer_class = CarrinhoSerializer
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

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
