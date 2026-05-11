import asyncio, os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
ADMIN_USER = os.environ.get("ADMIN_USER", "@AlgenisMods")

CARPETA_ARCHIVOS = "archivos"
ARCHIVO_COMANDOS = "comandos.json"
USERS_FILE = "users.json"

os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)

EMOJIS_NUMEROS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
MENSAJE_ENTREGA = "☝️Aquí Está Tu Texto Ya Listo 😈🔥"
esperando_notificacion = {}
esperando_archivo = {}

def cargar_comandos():
    if os.path.exists(ARCHIVO_COMANDOS):
        with open(ARCHIVO_COMANDOS) as f: return json.load(f)
    return {}

def guardar_comandos(c):
    with open(ARCHIVO_COMANDOS, 'w') as f: json.dump(c, f)

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
        return f"Texto {n}"
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
    await q.answer()
    cmds = cargar_comandos()
    if not cmds:
        await q.edit_message_text("⚠️ No hay textos disponibles.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Regresar", callback_data="menu")]]))
        return
    botones = [[InlineKeyboardButton(nombre_limpio(c), callback_data=f"cmd_{c}")] for c in cmds]
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

async def enviar_archivo(update, context):
    cmd = update.message.text[1:].split('@')[0].lower()
    cmds = cargar_comandos()
    if cmd not in cmds:
        return
    ruta = os.path.join(CARPETA_ARCHIVOS, cmds[cmd])
    if not os.path.isfile(ruta):
        await update.message.reply_text("⚠️ El archivo ya no está disponible.")
        return
    teclado = [[InlineKeyboardButton("🔙 Regresar", callback_data="menu"), InlineKeyboardButton("📂 Abrir", callback_data="abrir_ok")]]
    with open(ruta, 'rb') as f:
        await update.message.reply_document(document=f, caption=MENSAJE_ENTREGA, reply_markup=InlineKeyboardMarkup(teclado))

async def callback_archivo(update, context):
    _, cmd = update.callback_query.data.split('_', 1)
    cmds = cargar_comandos()
    if cmd not in cmds:
        await update.callback_query.answer("No disponible")
        return
    ruta = os.path.join(CARPETA_ARCHIVOS, cmds[cmd])
    if not os.path.isfile(ruta):
        await update.callback_query.answer("Archivo no encontrado")
        return
    teclado = [[InlineKeyboardButton("🔙 Regresar", callback_data="menu"), InlineKeyboardButton("📂 Abrir", callback_data="abrir_ok")]]
    with open(ruta, 'rb') as f:
        await update.callback_query.message.reply_document(document=f, caption=MENSAJE_ENTREGA, reply_markup=InlineKeyboardMarkup(teclado))

async def abrir_ok(update, context):
    await update.callback_query.answer("El archivo ya está arriba ☝️")

async def cmd_subir(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    if not context.args:
        await update.message.reply_text("Uso: /subir [comando]")
        return
    esperando_archivo[update.effective_user.id] = context.args[0].lower()
    await update.message.reply_text("📂 Envíame el archivo .txt ahora.")

async def recibir_documento(update, context):
    uid = update.effective_user.id
    if uid not in esperando_archivo:
        return
    cmd = esperando_archivo.pop(uid)
    doc = update.message.document
    if not doc.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Solo .txt")
        return
    filename = f"{cmd}.txt"
    archivo = await doc.get_file()
    await archivo.download_to_drive(os.path.join(CARPETA_ARCHIVOS, filename))
    cmds = cargar_comandos()
    cmds[cmd] = filename
    guardar_comandos(cmds)
    await update.message.reply_text(f"✅ Comando /{cmd} listo.")

async def cmd_del(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    if not context.args:
        await update.message.reply_text("Uso: /del [comando]")
        return
    cmd = context.args[0].lower()
    cmds = cargar_comandos()
    if cmd in cmds:
        ruta = os.path.join(CARPETA_ARCHIVOS, cmds[cmd])
        if os.path.exists(ruta): os.remove(ruta)
        del cmds[cmd]
        guardar_comandos(cmds)
        await update.message.reply_text(f"✅ /{cmd} eliminado.")
    else:
        await update.message.reply_text("No existe.")

async def cmd_list(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    cmds = cargar_comandos()
    if not cmds:
        await update.message.reply_text("No hay comandos.")
        return
    txt = "📋 *Comandos:*\n" + "\n".join([f"/{c} → {cmds[c]}" for c in cmds])
    await update.message.reply_text(txt, parse_mode="Markdown")

async def notificar(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    texto = update.message.text.partition(' ')[2]
    if texto:
        usuarios = cargar_usuarios()
        enviados = sum(1 for u in usuarios if not enviar_msg(context, u, texto))
        await update.message.reply_text(f"✅ Enviado a {enviados} usuario(s).")
    else:
        esperando_notificacion[update.effective_user.id] = True
        await update.message.reply_text("📝 Escribe el mensaje para todos:")

def enviar_msg(context, uid, texto):
    try:
        context.bot.send_message(chat_id=uid, text=f"🔔 *Actualización:*\n{texto}", parse_mode="Markdown")
        return False
    except:
        return True

async def texto_notificacion(update, context):
    uid = update.effective_user.id
    if esperando_notificacion.pop(uid, False):
        texto = update.message.text
        usuarios = cargar_usuarios()
        enviados = sum(1 for u in usuarios if not enviar_msg(context, u, texto))
        await update.message.reply_text(f"✅ Enviado a {enviados} usuario(s).")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notify", notificar))
    app.add_handler(CommandHandler("subir", cmd_subir))
    app.add_handler(CommandHandler("del", cmd_del))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CallbackQueryHandler(start, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(ver_textos, pattern="^ver_textos$"))
    app.add_handler(CallbackQueryHandler(ayuda, pattern="^ayuda$"))
    app.add_handler(CallbackQueryHandler(contacto, pattern="^contacto$"))
    app.add_handler(CallbackQueryHandler(abrir_ok, pattern="^abrir_ok$"))
    app.add_handler(CallbackQueryHandler(callback_archivo, pattern="^cmd_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_notificacion))
    app.add_handler(MessageHandler(filters.Document.TXT, recibir_documento))
    print("✅ Bot definitivo activo en /storage/emulated/0/bot/")
    app.run_polling()

if __name__ == "__main__":
    main()
