# Reloj — App Android (Kivy)

Clon del Reloj de iOS con estética *Liquid Glass*, hecho en Python + Kivy.
Incluye: **Reloj mundial**, **Alarma**, **Cronómetro** y **Temporizador**.

El APK se compila **en la nube** con GitHub Actions — no necesitas Linux ni
instalar nada pesado en tu PC.

---

## Cómo obtener el APK (paso a paso)

### 1. Crea un repositorio en GitHub
- Entra a <https://github.com/new>
- Ponle un nombre (p. ej. `reloj-android`), déjalo **público** o privado, y créalo.

### 2. Sube este proyecto
Desde esta carpeta (`reloj-android`), en PowerShell:

```powershell
git init
git add .
git commit -m "Reloj Liquid Glass para Android"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/reloj-android.git
git push -u origin main
```

> Reemplaza `TU_USUARIO` por tu usuario de GitHub.
> Si te pide login, usa tu usuario y un **token** (GitHub ya no acepta contraseña):
> créalo en <https://github.com/settings/tokens> con permiso `repo`.

### 3. Espera la compilación
- Ve a la pestaña **Actions** de tu repositorio.
- Verás el flujo **"Compilar APK"** ejecutándose (la **primera vez tarda
  ~20–40 min** porque descarga el SDK/NDK de Android; las siguientes son
  mucho más rápidas gracias a la caché).

### 4. Descarga el APK
- Cuando termine (✅ verde), entra al run.
- Abajo, en **Artifacts**, descarga **`reloj-apk`**.
- Dentro está el archivo `.apk`.

### 5. Instálalo en tu móvil
- Pásalo al teléfono.
- Ábrelo y permite **"Instalar apps de orígenes desconocidos"** si lo pide.
- ¡Listo!

---

## Previsualizar en el PC (opcional)
Si tienes Python **3.11 o 3.12** (Kivy aún no soporta 3.14):

```powershell
pip install "kivy[base]" plyer tzdata
python main.py
```

---

## Archivos del proyecto
| Archivo | Para qué sirve |
|---|---|
| `main.py` | La app completa (Kivy). |
| `buildozer.spec` | Configuración del empaquetado Android. |
| `.github/workflows/build-apk.yml` | Receta que compila el APK en la nube. |
| `.gitignore` | Evita subir archivos de compilación. |

## Notas
- Es un APK **debug** (firmado de prueba) — perfecto para instalar y usar tú.
  Para publicar en Google Play haría falta un build **release** firmado.
- Las horas usan `tzdata` (horario de verano correcto), sin depender de internet.
