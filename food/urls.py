from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GoogleLoginView

from .views import (
    UsuarioViewSet, RestauranteViewSet, CategoriaProdutoViewSet, ProdutoViewSet,
    CarrinhoViewSet, PedidoViewSet, PagamentoViewSet,
    EntregaViewSet, AvaliacaoRestauranteViewSet, AvaliacaoEntregadorViewSet, AvaliacaoProdutoViewSet
)


router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'restaurantes', RestauranteViewSet)
router.register(r'categorias', CategoriaProdutoViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'carrinhos', CarrinhoViewSet)
router.register(r'pedidos', PedidoViewSet)
router.register(r'pagamentos', PagamentoViewSet)
router.register(r'entregas', EntregaViewSet)
router.register(r'avaliacoes/restaurantes', AvaliacaoRestauranteViewSet)
router.register(r'avaliacoes/entregadores', AvaliacaoEntregadorViewSet)
router.register(r'avaliacoes/produtos', AvaliacaoProdutoViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
]
