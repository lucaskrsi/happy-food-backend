from rest_framework import serializers
from .models import (
    Opcao, Usuario, Restaurante, CategoriaProduto, Produto,
    Carrinho, ItemCarrinho, Pedido, ItemPedido, Pagamento,
    Entrega, RastreamentoEntrega,
    AvaliacaoRestaurante, AvaliacaoEntregador, AvaliacaoProduto
)

# -----------------------------
# USUÁRIOS E PERFIS
# -----------------------------
class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'telefone', 'foto', 'password', 'perfil']

    def create(self, validated_data):
        foto = validated_data.pop('foto', None)
        password = validated_data.pop('password', None)
        usuario = Usuario.objects.create_user(**validated_data)
        
        if foto:
            usuario.foto = foto
        if password:
            usuario.set_password(password)
            usuario.save()

        return usuario

# -----------------------------
# RESTAURANTES E CARDÁPIO
# -----------------------------
class CategoriaProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProduto
        fields = ['id', 'nome']


class ProdutoSerializer(serializers.ModelSerializer):
    categoria = CategoriaProdutoSerializer(read_only=True)
    restaurante = serializers.StringRelatedField()

    class Meta:
        model = Produto
        fields = ['id', 'nome', 'descricao', 'preco', 'imagem', 'disponivel', 'categoria', 'restaurante']


class RestauranteSerializer(serializers.ModelSerializer):
    produtos = ProdutoSerializer(many=True, read_only=True)
    dono = serializers.StringRelatedField()

    class Meta:
        model = Restaurante
        fields = ['id', 'nome', 'cnpj', 'endereco', 'aberto', 'produtos', 'dono']


# -----------------------------
# CARRINHO E PEDIDOS
# -----------------------------

class OpcaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opcao
        fields = ['id', 'nome', 'preco_adicional']

class ItemCarrinhoSerializer(serializers.ModelSerializer):
    produto = ProdutoSerializer(read_only=True)
    opcoes_escolhidas = OpcaoSerializer(many=True, read_only=True)

    class Meta:
        model = ItemCarrinho
        fields = ['id', 'produto', 'quantidade', 'observacao', 'opcoes_escolhidas' 'subtotal']


class CarrinhoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()
    itens = ItemCarrinhoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrinho
        fields = ['id', 'usuario', 'criado_em', 'itens']


class ItemPedidoSerializer(serializers.ModelSerializer):
    produto = ProdutoSerializer(read_only=True)
    opcoes = serializers.JSONField(read_only=True)

    class Meta:
        model = ItemPedido
        fields = ['id', 'produto', 'quantidade', 'preco_unitario', 'observacao', 'opcoes', 'subtotal']


class PedidoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()
    restaurante = serializers.StringRelatedField()
    itens = ItemPedidoSerializer(many=True, read_only=True)
    numero_formatado = serializers.ReadOnlyField()

    class Meta:
        model = Pedido
        fields = ['id', 'usuario', 'restaurante', 'valor_total', 'status', 'criado_em', 'itens', 'numero_formatado']


# -----------------------------
# PAGAMENTO
# -----------------------------
class PagamentoSerializer(serializers.ModelSerializer):
    pedido = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Pagamento
        fields = ['id', 'pedido', 'metodo', 'valor', 'status', 'criado_em']


# -----------------------------
# ENTREGA E RASTREAMENTO
# -----------------------------
class RastreamentoEntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RastreamentoEntrega
        fields = ['id', 'latitude', 'longitude', 'registrado_em']


class EntregaSerializer(serializers.ModelSerializer):
    pedido = serializers.PrimaryKeyRelatedField(read_only=True)
    entregador = serializers.StringRelatedField()
    rastreamentos = RastreamentoEntregaSerializer(many=True, read_only=True)

    class Meta:
        model = Entrega
        fields = ['id', 'pedido', 'entregador', 'status', 'inicio', 'fim', 'rastreamentos']


# -----------------------------
# AVALIAÇÕES
# -----------------------------
class AvaliacaoRestauranteSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()

    class Meta:
        model = AvaliacaoRestaurante
        fields = ['id', 'usuario', 'nota', 'comentario', 'criado_em']


class AvaliacaoEntregadorSerializer(serializers.ModelSerializer):
    entregador = serializers.StringRelatedField()
    usuario = serializers.StringRelatedField()

    class Meta:
        model = AvaliacaoEntregador
        fields = ['id', 'entregador', 'usuario', 'nota', 'comentario', 'criado_em']


class AvaliacaoProdutoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()
    produto = serializers.StringRelatedField()

    class Meta:
        model = AvaliacaoProduto
        fields = ['id', 'produto', 'usuario', 'nota', 'comentario', 'criado_em']
