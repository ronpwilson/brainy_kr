import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.services.ai_service import AIService
from app.services.document_service import DocumentService


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
ai_service = AIService()
document_service = DocumentService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the RBI Grade B AI Study Assistant.\n\n"
        "Use /ask followed by your question.\n"
        "Example: /ask Explain inflation targeting in India"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the assistant\n"
        "/help - Show help\n"
        "/ask <question> - Ask a study question"
    )


async def ask(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    question = " ".join(context.args).strip()

    if not question:
        await update.message.reply_text(
            "Please provide a question.\n\n"
            "Example:\n"
            "/ask What is monetary policy transmission?"
        )
        return

    user_id = (
        update.effective_user.id
        if update.effective_user
        else None
    )

    await update.message.reply_text(
        "🔎 Searching your study material..."
    )

    try:
        results = document_service.search(
            query=question,
            user_id=user_id,
        )

        if not results:
            await update.message.reply_text(
                "I couldn't find relevant content in your uploaded documents."
            )
            return

        context_text = "\n\n".join(
            (
                f"[Source: {result['filename']}, "
                f"Page: {result['page_number']}]\n"
                f"{result['text']}"
            )
            for result in results
        )

        await update.message.reply_text(
            "🤖 Generating answer..."
        )

        answer = ai_service.answer_from_context(
            question=question,
            context=context_text,
        )

        sources = "\n".join(
            f"• {result['filename']} — "
            f"Page {result['page_number']}"
            for result in results
        )

        response = (
            f"{answer}\n\n"
            f"📚 Sources:\n{sources}"
        )

        await update.message.reply_text(response[:4000])

    except Exception:
        logger.exception("Failed to answer question using RAG")

        await update.message.reply_text(
            "❌ I couldn't generate an answer from the study material."
        )

async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    document = update.message.document

    if document is None:
        return

    filename = document.file_name or "uploaded_document"
    suffix = Path(filename).suffix.lower()
    mime_type = (document.mime_type or "").lower()

    # Only accept PDFs for now.
    if suffix != ".pdf" and mime_type != "application/pdf":
        await update.message.reply_text(
            "Please send a PDF document for study material."
        )
        return

    settings = get_settings()
    max_size = settings.max_document_size_mb * 1024 * 1024

    if (
        document.file_size is not None
        and document.file_size > max_size
    ):
        await update.message.reply_text(
            f"This PDF is too large. "
            f"The configured limit is "
            f"{settings.max_document_size_mb} MB."
        )
        return

    try:
        await update.message.reply_text(
            f"📄 Received: {filename}\n"
            "Downloading temporarily for processing..."
        )

        # Automatically deletes the directory and PDF after the block.
        with tempfile.TemporaryDirectory(
            prefix="rbi_upload_"
        ) as temp_dir:

            temp_path = Path(temp_dir) / Path(filename).name

            telegram_file = await document.get_file(
                read_timeout=60,
                connect_timeout=30,
            )

            await telegram_file.download_to_drive(
                custom_path=temp_path,
                read_timeout=120,
                connect_timeout=30,
            )

            result = document_service.process_pdf(
                file_path=temp_path,
                original_filename=filename,
                user_id=(
                    update.effective_user.id
                    if update.effective_user
                    else None
                ),
            )

            size_mb = result["size_bytes"] / (1024 * 1024)

            await update.message.reply_text(
                f"✅ {filename} processed.\n\n"
                f"Pages with extracted text: {result['page_count']}\n"
                f"Text chunks created: {result['chunk_count']}\n"
                f"Chunks stored in ChromaDB: {result['stored_chunk_count']}\n"
                f"Size: {size_mb}\n\n"
                "📚 Study material is now available for RAG."
            )

    except Exception:
        logger.exception(
            "Failed to receive document: %s",
            filename,
        )

        await update.message.reply_text(
            "❌ I couldn't process that PDF. Please try again."
        )

    finally:
        logger.info(
            "Temporary document cleanup completed for %s",
            filename,
        )

async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    question = update.message.text

    user_id = (
        update.effective_user.id
        if update.effective_user
        else None
    )

    try:
        results = document_service.search(
            query=question,
            user_id=user_id,
        )

        if not results:
            await update.message.reply_text(
                "I couldn't find relevant content in your uploaded documents."
            )
            return

        response = "🔎 Relevant chunks found:\n\n"

        for index, result in enumerate(results, start=1):
            response += (
                f"--- Result {index} ---\n"
                f"📄 {result['filename']}\n"
                f"📖 Page: {result['page_number']}\n\n"
                f"{result['text']}\n\n"
            )

        await update.message.reply_text(response[:4000])

    except Exception:
        logger.exception("Failed to search documents")
        await update.message.reply_text(
            "❌ I couldn't search the uploaded documents."
        )


def main():
    settings = get_settings()

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ask", handle_ask))
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_document)
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ask,
        )
    )

    logger.info("Starting RBI Grade B Telegram bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
