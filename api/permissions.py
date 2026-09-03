from rest_framework import permissions


class PermisoEscrituraPorModelo(permissions.BasePermission):
    """Regla de asignación por roles.

    Lectura (métodos seguros): pública.
    Escritura: solo usuarios autenticados que tengan el permiso de modelo de
    Django correspondiente a la acción (POST -> add, PUT/PATCH -> change,
    DELETE -> delete) sobre el modelo del ViewSet. Los grupos se crean en
    nursery/accesos.py: "admin" tiene todos los permisos; "operario" tiene
    add/change/view sobre Medicion, Evaluacion, Evento y Foto, y change/view
    sobre Planta (docs/plan.md §9).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        if usuario.is_superuser:
            return True
        accion = {
            "POST": "add",
            "PUT": "change",
            "PATCH": "change",
            "DELETE": "delete",
        }.get(request.method)
        modelo = view.queryset.model
        permiso = f"{modelo._meta.app_label}.{accion}_{modelo._meta.model_name}"
        return usuario.has_perm(permiso)
