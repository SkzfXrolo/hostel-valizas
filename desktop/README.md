# Valizas Reservas (EXE)

App de escritorio para Leonardo & Rubén:

- **WhatsApp en vivo (QR)** → mensajes entrantes → IA → reserva
- Pegar mensaje a mano (fallback)
- Calendario con días ocupados y a nombre de quién
- Tarifas mensuales editables (USD)
- Matching por capacidad + fotos de habitación
- IA **gratuita**: Groq o Gemini (sin key → reglas en español)

## Correr en desarrollo

```bash
cd desktop
pip install -r requirements.txt
cd whatsapp-bridge && npm install && cd ..
python main.py
```

## WhatsApp en vivo (Lo Gordo)

1. Instalá **Node.js LTS** gratis: https://nodejs.org
2. En la app: pestaña **1 · WhatsApp** → **Conectar / Mostrar QR**
3. En el celular: WhatsApp → Dispositivos vinculados → Vincular dispositivo
4. Escaneá el QR que aparece en la app
5. Cuando llegue un mensaje, tocá **Usar este mensaje** → **Analizar con IA** → **Crear reserva**

Nota: usa Baileys (WhatsApp Web no oficial). No es la API Business de Meta.

## IA gratuita

En **5 · Config / IA**:

1. **Groq (recomendado)**: https://console.groq.com → API Keys → pegá `gsk_...`
2. **Gemini**: https://aistudio.google.com/apikey → pegá la key
3. Proveedor: `auto` (prueba Groq → Gemini → OpenAI → reglas)

Sin key igual entiende fechas/personas/dormitorio con reglas.

## Generar EXE

```bash
cd desktop
pip install -r requirements.txt
pyinstaller ValizasReservas.spec --noconfirm
```

El ejecutable queda en `desktop/dist/ValizasReservas.exe`.
La primera vez que conectés WhatsApp, la app instalará dependencias Node del bridge (hace falta Node instalado en la PC).
