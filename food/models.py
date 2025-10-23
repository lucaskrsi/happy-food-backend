from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser, Group, Permission
from django.db.models.signals import pre_save
from django.dispatch import receiver
import os


# -----------------------------
# USUÁRIOS E PERFIS
# -----------------------------
class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("O campo username é obrigatório")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if 'foto' in extra_fields:
            user.foto = extra_fields['foto']
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)



class Usuario(AbstractUser):
    telefone = models.CharField(max_length=20, blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    foto = models.ImageField(upload_to="usuarios/fotos/", null=True, blank=True)
    foto_url = models.URLField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    related_name = "usuarios"
    groups = models.ManyToManyField(
        Group, related_name="usuario_set", blank=True
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="usuario_permissions_set",
        blank=True,
    )

    objects = UsuarioManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    def __str__(self):
        return self.username or self.email

@receiver(pre_save, sender=Usuario)
def apagar_foto_antiga(sender, instance, **kwargs):
    if not instance.pk:
        return False

    try:
        foto_antiga = Usuario.objects.get(pk=instance.pk).foto
    except Usuario.DoesNotExist:
        return False

    nova_foto = instance.foto
    if foto_antiga and foto_antiga != nova_foto:
        if os.path.isfile(foto_antiga.path):
            os.remove(foto_antiga.path)

class PerfilUsuario(models.Model):
    TIPO_CHOICES = [
        ("cliente", "Cliente"),
        ("restaurante", "Restaurante"),
        ("entregador", "Entregador"),
        ("admin", "Administrador"),
    ]

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="perfis"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo}"


# -----------------------------
# RESTAURANTES E CARDÁPIO
# -----------------------------
class Restaurante(models.Model):
    dono = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="restaurantes"
    )
    nome = models.CharField(max_length=100)
    cnpj = models.CharField(max_length=20, unique=True)
    endereco = models.TextField()
    aberto = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class CategoriaProduto(models.Model):
    nome = models.CharField(max_length=50)

    def __str__(self):
        return self.nome


class Produto(models.Model):
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="produtos"
    )
    categoria = models.ForeignKey(
        CategoriaProduto, on_delete=models.SET_NULL, null=True, blank=True
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to="produtos/", blank=True, null=True)
    disponivel = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} - {self.restaurante.nome}"


# -----------------------------
# CARRINHO E PEDIDOS
# -----------------------------
class Carrinho(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="carrinhos"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrinho de {self.usuario.username}"


class ItemCarrinho(models.Model):
    carrinho = models.ForeignKey(
        Carrinho, on_delete=models.CASCADE, related_name="itens"
    )
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    observacao = models.TextField(blank=True, null=True)

    def subtotal(self):
        return self.produto.preco * self.quantidade

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"


class Pedido(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("em_preparo", "Em preparo"),
        ("a_caminho", "A caminho"),
        ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ]

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="pedidos"
    )
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="pedidos"
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pendente")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.username}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(blank=True, null=True)

    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"


# -----------------------------
# PAGAMENTO
# -----------------------------
class Pagamento(models.Model):
    METODO_CHOICES = [
        ("pix", "Pix"),
        ("cartao_credito", "Cartão de Crédito"),
        ("cartao_debito", "Cartão de Débito"),
        ("dinheiro", "Dinheiro"),
    ]

    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE, related_name="pagamento"
    )
    metodo = models.CharField(max_length=30, choices=METODO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, default="pendente")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento {self.metodo} - Pedido {self.pedido.id}"


# -----------------------------
# ENTREGA E RASTREAMENTO
# -----------------------------
class Entrega(models.Model):
    STATUS_CHOICES = [
        ("aguardando", "Aguardando"),
        ("retirado", "Retirado"),
        ("em_rota", "Em rota"),
        ("entregue", "Entregue"),
    ]

    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE, related_name="entrega"
    )
    entregador = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name="entregas"
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="aguardando"
    )
    inicio = models.DateTimeField(null=True, blank=True)
    fim = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Entrega #{self.id} - Pedido {self.pedido.id}"


class RastreamentoEntrega(models.Model):
    entrega = models.ForeignKey(
        Entrega, on_delete=models.CASCADE, related_name="rastreamentos"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    registrado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.latitude}, {self.longitude}"


# -----------------------------
# AVALIAÇÕES
# -----------------------------
class AvaliacaoRestaurante(models.Model):
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="avaliacoes"
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Avaliação {self.nota}/5 - {self.restaurante.nome}"


class AvaliacaoEntregador(models.Model):
    entregador = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="avaliacoes_recebidas"
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="avaliacoes_enviadas"
    )
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entregador.username} - {self.nota}/5"


class AvaliacaoProduto(models.Model):
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="avaliacoes"
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.produto.nome} - {self.nota}/5"
