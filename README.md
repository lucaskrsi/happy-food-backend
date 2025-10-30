# 🍔 Happy Food – API Backend (Django REST Framework)

API para uma plataforma de delivery com usuários, restaurantes, produtos, carrinho, pedidos, entregas e avaliações.  
Desenvolvido com **Django** e **Django REST Framework**.

---

## ⚙️ Instalação e configuração

### 1️⃣ Clone o repositório

```bash
git clone https://github.com/lucaskrsi/happy-food-backend.git
cd happy-food-backend
```

### 2️⃣ Crie e ative o ambiente virtual

```bash
python -m venv venv
venv\Scripts\activate  # no Windows
# ou
source venv/bin/activate  # no Linux/Mac
```

### 3️⃣ Instale as dependências

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure o banco de dados

Edite `settings.py` (use PostgreSQL em produção):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 5️⃣ Execute as migrações

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6️⃣ Crie um superusuário

```bash
python manage.py createsuperuser
```

### 7️⃣ Inicie o servidor

```bash
python manage.py runserver
```

Acesse:  
➡️ http://127.0.0.1:8000/admin  
➡️ http://127.0.0.1:8000/api/

---

## 🔐 Autenticação e Registro

### ✅ 1. Registro Manual (usuário padrão)

**Endpoint:** `POST /usuarios/`

```json
{
  "username": "bruno",
  "email": "bruno@email.com",
  "password": "123456",
  "tipo": "restaurante"
}
```

> 🔸 Por padrão Cria automaticamente um perfil `cliente`.

---

### ✅ 2. Registro como restaurante

Após criar o usuário, envie:

**Endpoint:** `POST /usuarios/definir_tipo_usuario/`  
**Autenticação:** Bearer Token

```json
{
    "nome": "Pizzaria Bucciarati",
    "cnpj": "99.999.999/0001-99",
    "endereco": "Rua Arrivederci, 6"
}
```

---

### ✅ 3. Login tradicional

**Endpoint:** `POST /auth/token/`

```json
{
  "username": "bruno",
  "password": "123456"
}
```

Retorna:
```json
{
  "access": "jwt_token_aqui",
  "refresh": "refresh_token_aqui"
}
```

Use o token JWT no cabeçalho das próximas requisições:
```
Authorization: Bearer <token>
```

---

### ✅ 4. Login com Google

#### 1️⃣ Configure o OAuth2 no Google Cloud
- Vá em [https://console.cloud.google.com/](https://console.cloud.google.com/)
- Crie um projeto e ative o **OAuth consent screen**
- Adicione o redirect URI:
  ```
  http://localhost:8000/auth/google/login/callback/
  ```

#### 2️⃣ Adicione as chaves no `.env` ou `settings.py`:
```python
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": "SEU_CLIENT_ID",
            "secret": "SEU_CLIENT_SECRET",
            "key": ""
        }
    }
}
```

#### 3️⃣ URL para login com Google
**Endpoint:**  
```
GET /auth/google/login/
```

Isso redireciona o usuário para o login Google e retorna um token JWT.  
Depois do login, o `Usuario` é criado automaticamente e o sinal cria o `PerfilUsuario`.

---

## 🍽️ Principais Rotas da API

### 👤 Usuários
| Método | Rota | Descrição |
|--------|-------|-----------|
| `GET` | `/usuarios/` | Lista todos os usuários |
| `POST` | `/usuarios/` | Cria novo usuário (cliente por padrão) |
| `GET` | `/usuarios/{id}/` | Detalhes de um usuário |
| `PUT` / `PATCH` | `/usuarios/{id}/` | Atualiza dados |
| `DELETE` | `/usuarios/{id}/` | Exclui usuário |

---

### 🍔 Restaurantes
| Método | Rota | Descrição |
|--------|-------|-----------|
| `GET` | `/restaurantes/` | Lista restaurantes |
| `GET` | `/restaurantes/{id}` | Detalhes de um restaurante |
| `POST` | `/restaurantes/` | Cadastra novo restaurante (se não informado, o dono será o usuário logado) |
| `GET` | `/restaurantes/{id}/produtos/` | Lista produtos do restaurante |

---

### 🛒 Carrinho
| Método | Rota | Descrição |
|--------|-------|-----------|
| `GET` | `/carrinhos/` | Lista carrinhos |
| `POST` | `/carrinhos/{id}/adicionar_item/` | Adiciona produto ao carrinho |
| `DELETE` | `/carrinhos/{id}/` | Esvazia o carrinho |

---

### 📦 Pedidos e Pagamentos
| Método | Rota | Descrição |
|--------|-------|-----------|
| `GET` | `/pedidos/` | Lista pedidos do usuário |
| `POST` | `/pedidos/` | Cria um novo pedido |
| `POST` | `/pedidos/{id}/alterar_status/` | Restaurante/adm altera status |
| `GET` | `/pedidos/{id}/pagamento/` | Consulta status do pagamento |

---

### 🚴‍♂️ Entregas e Rastreamento
| Método | Rota | Descrição |
|--------|-------|-----------|
| `GET` | `/entregas/` | Lista entregas |
| `POST` | `/entregas/{id}/atualizar_localizacao/` | Entregador atualiza GPS |
| `GET` | `/rastreamentoentrega/` | Mostra rota da entrega |

---

### ⭐ Avaliações
| Método | Rota | Descrição |
|--------|-------|-----------|
| `POST` | `/avaliacaorestaurante/` | Avaliar restaurante |
| `POST` | `/avaliacaoentregador/` | Avaliar entregador |
| `POST` | `/avaliacaoproduto/` | Avaliar produto |

---

## 🗺️ Estrutura de diretórios

```
happy_food_backend/
├── food/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── view_auth.py
│   ├── view_logout.py
│   └── views.py
├── happy_food_backend/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

---

## 🧩 Próximos passos

- [ ] Criar sistemas de cupons e descontos
- [ ] Integrar pagamento real (ex: Stripe ou Mercado Pago)
- [ ] Adicionar notificação em tempo real (ex: via WebSocket ou Firebase)
- [ ] Implementar testes automatizados com `pytest`

---

## 👨‍💻 Autor

**Lucas Silva**  
Desenvolvedor Fullstack  
💼 Linkedin: linkedin.com/in/lucas-pereira-da-silva/  
📧 Contato: lucas.silva.code@outlook.com.br
