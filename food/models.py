from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser, Group, Permission
from django.db.models.signals import pre_save
from django.dispatch import receiver
import os
import uuid
from django.db import transaction
from django.utils import timezone


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
        extra_fields.setdefault("perfil", 'suporte')
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)



class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    foto = models.ImageField(upload_to="usuarios/fotos/", null=True, blank=True)
    foto_url = models.URLField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    TIPO_CHOICES = [
        ("cliente", "Cliente"),
        ("restaurante", "Restaurante"),
        ("entregador", "Entregador"),
        ("suporte", "Suporte"),
    ]
    perfil = models.CharField(max_length=20, choices=TIPO_CHOICES, default="cliente")
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

# -----------------------------
# RESTAURANTES E CARDÁPIO
# -----------------------------
class Restaurante(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50)

    def __str__(self):
        return self.nome


class Produto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
# OPÇÕES ADICIONAIS DO PRODUTO
# -----------------------------

class GrupoOpcao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='grupos_opcoes')
    nome = models.CharField(max_length=100)
    obrigatorio = models.BooleanField(default=False)
    multipla_escolha = models.BooleanField(default=False)

    def __str__(self):
        return self.nome


class Opcao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grupo = models.ForeignKey(GrupoOpcao, on_delete=models.CASCADE, related_name='opcoes')
    nome = models.CharField(max_length=100)
    preco_adicional = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return self.nome


# -----------------------------
# CARRINHO E PEDIDOS
# -----------------------------
class Carrinho(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="carrinhos"
    )
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="carrinhos",
        blank=True, null=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'restaurante')

    def __str__(self):
        return f"Carrinho de {self.usuario.username}"


class ItemCarrinho(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrinho = models.ForeignKey(
        Carrinho, on_delete=models.CASCADE, related_name="itens"
    )
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    observacao = models.TextField(blank=True, null=True)
    opcoes_escolhidas = models.ManyToManyField(Opcao, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for grupo in {op.grupo for op in self.opcoes_escolhidas.all()}:
            opcoes_no_grupo = self.opcoes_escolhidas.filter(grupo=grupo)
            if not grupo.multipla_escolha and opcoes_no_grupo.count() > 1:
                raise ValueError(f"O grupo de opções '{grupo.nome}' não permite múltiplas escolhas.")
            if grupo.obrigatorio and opcoes_no_grupo.count() == 0:
                raise ValueError(f"O grupo de opções '{grupo.nome}' é obrigatório.")

    def subtotal(self):
        preco_base = self.produto.preco
        adicionais = sum(op.preco_adicional for op in self.opcoes_escolhidas.all())
        return (preco_base + adicionais) * self.quantidade

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"


class Pedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    numero_pedido = models.PositiveIntegerField(default=1)
    restaurante = models.ForeignKey(
        Restaurante, on_delete=models.CASCADE, related_name="pedidos"
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pendente")
    criado_em = models.DateTimeField(auto_now_add=True)
    data_referencia = models.DateField()
    endereco_entrega = models.TextField(blank=True, null=True)
    endereco_origem = models.TextField(blank=True, null=True)

    class Meta:
       # Isso aqui é para não repetir o mesmo número de pedido para o mesmo restaurante
       unique_together = ('restaurante', 'numero_pedido', 'data_referencia')

    def __str__(self):
        return f"Pedido {self.numero_pedido:04d} - {self.restaurante.nome}"
    
    def save(self, *args, **kwargs):
        if not self.data_referencia:
            self.data_referencia = timezone.now().date()

        if not self.numero_pedido:
            with transaction.atomic():
                ultimo_pedido = Pedido.objects.select_for_update().filter(restaurante=self.restaurante, data_referencia=self.data_referencia).order_by('-numero_pedido').first()
                if ultimo_pedido:
                    novo_numero = ultimo_pedido.numero_pedido + 1
                    if novo_numero > 99999:
                        novo_numero = 1
                else:
                    novo_numero = 1
                self.numero_pedido = novo_numero
        super().save(*args, **kwargs)
    @property
    def numero_formatado(self):
        return f"{self.numero_pedido:05d}"


class ItemPedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(blank=True, null=True)
    opcoes = models.JSONField(default=list)

    @classmethod
    def from_item_carrinho(cls, item_carrinho, pedido):
        opcoes_data = [
            {"nome": op.nome, "preco_adicional": str(op.preco_adicional)}
            for op in item_carrinho.opcoes_escolhidas.all()
        ]

        adicionais = sum(op['preco_adicional'] for op in opcoes_data)

        return cls(
            pedido = pedido,
            produto=item_carrinho.produto,
            quantidade=item_carrinho.quantidade,
            preco_unitario=item_carrinho.produto.preco + float(adicionais),
            observacao=item_carrinho.observacao,
            opcoes=opcoes_data
        )

    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome}"

# -----------------------------
# PAGAMENTO
# -----------------------------
class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ("aguardando", "Aguardando"),
        ("retirado", "Retirado"),
        ("em_rota", "Em rota"),
        ("entregue", "Entregue"),
    ]

    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE, related_name="entrega"
    )
    entregador = models.OneToOneField(
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="avaliacoes"
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.produto.nome} - {self.nota}/5"

class Endereco(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="enderecos"
    )
    restaurante = models.OneToOneField(
        Restaurante, on_delete=models.CASCADE, related_name="enderecos", null=True, blank=True
    )
    apelido = models.CharField(max_length=50, blank=True, null=True)
    tipo = models.CharField(max_length=50, blank=True, null=True)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    cep = models.CharField(max_length=20)
    criado_em = models.DateTimeField(auto_now_add=True)

    def gerar_snapshot(self, formato="texto"):
        if formato == "json":
            return {
                "rua": self.rua,
                "numero": self.numero,
                "bairro": self.bairro,
                "cidade": self.cidade,
                "estado": self.estado,
                "cep": self.cep,
            }
        return f"{self.rua}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado} - CEP {self.cep}"



    def __str__(self):
        return f"[{self.apelido}] ({self.cep}) {self.rua}, {self.numero} - {self.cidade}/{self.estado}"