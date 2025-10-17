from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """Admins podem qualquer coisa; outros só GETs"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser

class IsRestaurante(permissions.BasePermission):
    """Permite somente usuários que possuam o perfil 'restaurante'"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.perfis.filter(tipo='restaurante').exists()

class IsEntregador(permissions.BasePermission):
    """Permite somente entregadores"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.perfis.filter(tipo='entregador').exists()
