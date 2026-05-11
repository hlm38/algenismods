import asyncio, os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
COMANDOS = {}
ARCHIVO_CONFIG = "config.json"
USERS_FILE = "users.json"
MENSAJE_ENTREGA = "☝️Aquí Está Tu Texto Ya Listo 😈🔥"
ADMIN_USER = os.environ.get("ADMIN_USER", "@AlgenisMods")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

EMOJIS_NUMEROS = ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
esperando_notificacion = {}

def cargar_config():
    global COMANDOS
    if os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG) as f: COMANDOS = json.load(f)

def guardar_config():
    with open(ARCHIVO_CONFIG, 'w') as f: json.dump(COMANDOS, f)

def cargar_usuarios():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f: return set(json.load(f))
    return set()

def guardar_usuarios(u):
    with open(USERS_FILE, 'w') as f: json.dump(list(u), f)

def agregar_usuario(uid):
    u = cargar_usuarios()
    if uid not in u:
        u.add(uid)
        guardar_usuarios(u)

def nombre_limpio(cmd):
    if len(cmd) >= 4 and cmd.startswith('txt') and cmd[3:].isdigit():
        n = int(cmd[3:])
        if n <= 9:
            return f"Texto {EMOJIS_NUMEROS[n]}"
        else:
            return f"Texto {n}"
    if cmd.startswith('txt') and len(cmd) > 3:
        return "Texto " + cmd[3:].replace('_', ' ').title()
    return cmd[0].upper() + cmd[1:].replace('_', ' ')

async def start(update, context):
    uid = update.effective_user.id
    agregar_usuario(uid)
    teclado = [
        [InlineKeyboardButton("Ver Textos Disponibles ✨", callback_data="ver_textos")],
        [InlineKeyboardButton("ℹ️ Ayuda", callback_data="ayuda")],
        [InlineKeyboardButton("📞 Contacto", callback_data="contacto")]
    ]
    msg = "👋 *Bienvenido al Menú Principal*\n\nSelecciona una opción:"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(teclado))

async def ver_textos(update, context):
    q = update.callback_query
    agregar_usuario(q.from_user.id)
    await q.answer()
    if not COMANDOS:
        await q.edit_message_text("⚠️ No hay textos disponibles.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Regresar", callback_data="menu")]]))
        return
    botones = [[InlineKeyboardButton(nombre_limpio(c), callback_data=f"cmd_{c}")] for c in COMANDOS]
    botones.append([InlineKeyboardButton("🔙 Regresar", callback_data="menu")])
    await q.edit_message_text("📋 *Textos Disponibles:*\nElige uno para recibirlo.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(botones))

async def ayuda(update, context):
    q = update.callback_query
    await q.answer()
    t = "🤖 *Cómo Usar Este Bot:*\n\n• Usa el menú para ver los textos.\n• Al seleccionar uno, recibirás el archivo.\n• Todo es privado y seguro.\n\n¿Dudas? Contacta al administrador."
    await q.edit_message_text(t, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Regresar", callback_data="menu")]]))

async def contacto(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(f"📞 *Administrador:* {ADMIN_USER}\n\nEnvíale un mensaje directo para cualquier consulta.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Regresar", callback_data="menu")]]))

def crear_manejador(ruta):
    async def f(update, context):
        if not os.path.isfile(ruta):
            t = "⚠️ El archivo ya no está disponible."
            if update.callback_query:
                await update.callback_query.edit_message_text(t)
            else:
                await update.message.reply_text(t)
            return
        teclado = [[InlineKeyboardButton("🔙 Regresar", callback_data="menu"), InlineKeyboardButton("📂 Abrir", callback_data="abrir_ok")]]
        try:
            with open(ruta, 'rb') as arch:
                if update.callback_query:
                    await update.callback_query.message.reply_document(document=arch, caption=MENSAJE_ENTREGA, reply_markup=InlineKeyboardMarkup(teclado))
                else:
                    await update.message.reply_document(document=arch, caption=MENSAJE_ENTREGA, reply_markup=InlineKeyboardMarkup(teclado))
        except:
            m = "❌ Error al enviar. Intenta de nuevo."
            if update.callback_query:
                await update.callback_query.edit_message_text(m)
            else:
                await update.message.reply_text(m)
    return f

async def abrir_ok(update, context):
    await update.callback_query.answer("El archivo ya está arriba ☝️")

async def notificar(update, context):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return
    texto = update.message.text.partition(' ')[2]
    if texto:
        usuarios = cargar_usuarios()
        if not usuarios:
            await update.message.reply_text("No hay usuarios registrados.")
            return
        enviados = 0
        for u in usuarios:
            try:
                await context.bot.send_message(chat_id=u, text=f"🔔 *Nueva actualización:*\n{texto}", parse_mode="Markdown")
                enviados += 1
            except: pass
        await update.message.reply_text(f"✅ Notificación enviada a {enviados} usuario(s).")
    else:
        esperando_notificacion[uid] = True
        await update.message.reply_text("📝 *¿Qué mensaje deseas enviar a todos los usuarios?*\n\nEscríbelo ahora como respuesta a este chat.", parse_mode="Markdown")

async def manejar_respuesta_notificacion(update, context):
    uid = update.effective_user.id
    if esperando_notificacion.get(uid):
        texto = update.message.text
        del esperando_notificacion[uid]
        usuarios = cargar_usuarios()
        if not usuarios:
            await update.message.reply_text("No hay usuarios registrados.")
            return
        enviados = 0
        for u in usuarios:
            try:
                await context.bot.send_message(chat_id=u, text=f"🔔 *Nueva actualización:*\n{texto}", parse_mode="Markdown")
                enviados += 1
            except: pass
        await update.message.reply_text(f"✅ Notificación enviada a {enviados} usuario(s).")

def main():
    cargar_config()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notify", notificar))
    for cmd, ruta in COMANDOS.items():
        app.add_handler(CommandHandler(cmd, crear_manejador(ruta)))
    app.add_handler(CallbackQueryHandler(start, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(ver_textos, pattern="^ver_textos$"))
    app.add_handler(CallbackQueryHandler(ayuda, pattern="^ayuda$"))
    app.add_handler(CallbackQueryHandler(contacto, pattern="^contacto$"))
    app.add_handler(CallbackQueryHandler(abrir_ok, pattern="^abrir_ok$"))
    for cmd, ruta in COMANDOS.items():
        app.add_handler(CallbackQueryHandler(crear_manejador(ruta), pattern=f"^cmd_{cmd}$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_respuesta_notificacion))
    print("🤖 Bot en Render funcionando.")
    app.run_polling()

if __name__ == "__main__":
    main()
