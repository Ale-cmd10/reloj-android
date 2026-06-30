[app]

# Nombre visible de la app
title = Reloj

# Identificadores del paquete (cámbialos si publicas en una tienda)
package.name = relojios
package.domain = org.juliana

# Código fuente
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# Versión
version = 1.0

# Dependencias de Python que se empaquetan en el APK.
#  - kivy: la interfaz
#  - tzdata: base de zonas horarias (horario de verano correcto)
#  - plyer: vibración / notificaciones
#  - android: API de la plataforma
requirements = python3,kivy==2.3.0,tzdata,plyer,android

# Versión de python-for-android a usar (Buildozer la clona desde git).
# Se fija v2024.01.21 porque compila Python 3.11; las versiones más nuevas
# compilan Python 3.13, incompatible con los .c de Kivy 2.3.0.
p4a.branch = v2024.01.21

# Orientación
orientation = portrait
fullscreen = 0

# Permisos (INTERNET y VIBRATE por si luego añades sincronización online)
android.permissions = INTERNET,VIBRATE

# Niveles de API de Android
android.api = 34
android.minapi = 24
android.ndk_api = 24

# Arquitecturas (cubre la mayoría de móviles modernos)
android.archs = arm64-v8a,armeabi-v7a

# Aceptar automáticamente las licencias del SDK al compilar en CI
android.accept_sdk_license = True

# Color de la pantalla de carga / fondo
android.presplash_color = #0d1236

[buildozer]

# Verbosidad de los logs (2 = detallado, útil para depurar el build)
log_level = 2
warn_on_root = 1
