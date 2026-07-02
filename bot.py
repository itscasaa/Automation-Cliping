import sys
import os
import shutil
import asyncio
from pathlib import Path
import discord
from discord.ext import commands, tasks
import config
import db

# Pastikan tabel DB diinisialisasi
db.init_db()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"🤖 Bot Discord online sebagai {bot.user}")
    if not worker_loop.is_running():
        worker_loop.start()


@bot.command(name="queue")
async def queue_status(ctx):
    """Menampilkan status antrean saat ini."""
    status = db.get_queue_status()
    embed = discord.Embed(title="📋 Status Antrean Auto Clipper", color=discord.Color.blue())
    embed.add_field(name="⏳ Pending (Antre)", value=str(status["pending"]), inline=True)
    embed.add_field(name="⚙️ Processing (Diproses)", value=str(status["processing"]), inline=True)
    embed.add_field(name="✅ Completed (Selesai)", value=str(status["completed"]), inline=True)
    embed.add_field(name="❌ Failed (Gagal)", value=str(status["failed"]), inline=True)
    await ctx.send(embed=embed)


@bot.command(name="help")
async def bot_help(ctx):
    """Menampilkan panduan penggunaan perintah bot."""
    help_text = (
        "**🎬 Panduan Perintah Auto Clipper Bot**\n\n"
        "• `!clip <URL_YouTube> [type] [max_clips] [lang]`\n"
        "  Memasukkan video YouTube ke antrean pemotongan.\n"
        "  *Contoh:* `!clip https://youtu.be/abc podcast 3 id`\n\n"
        "• `!clip` (dengan mengunggah file video langsung)\n"
        "  Mengunggah file video lokal untuk dipotong.\n\n"
        "• Opsi parameter:\n"
        "  - `[type]`: `general`, `educational`, `podcast`, `gaming` (Default: `general`)\n"
        "  - `[max_clips]`: Jumlah maksimal klip hasil (Default: 5)\n"
        "  - `[lang]`: Kode bahasa video `id`, `en`, atau `None` (Default: `id`)\n\n"
        "• `!queue` / `!status`\n"
        "  Melihat jumlah video yang sedang mengantre di server."
    )
    await ctx.send(help_text)


@bot.command(name="clip")
async def clip_video(
    ctx,
    url: str = None,
    content_type: str = "general",
    max_clips: int = 5,
    lang: str = "id",
):
    """Command untuk memicu pemrosesan video."""
    # Validasi content_type
    valid_types = {"general", "educational", "podcast", "gaming"}
    if content_type not in valid_types:
        await ctx.send(
            f"❌ Tipe konten '{content_type}' tidak valid. Pilih salah satu dari: {', '.join(valid_types)}"
        )
        return

    # Saring input bahasa
    if lang == "None" or lang == "none":
        lang = None

    # Cek apakah ada attachment video
    file_path = None
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        # Cek tipe file
        ext = Path(attachment.filename).suffix.lower()
        from downloader.local import SUPPORTED_FORMATS

        if ext not in SUPPORTED_FORMATS:
            await ctx.send(
                f"❌ Format file '{ext}' tidak didukung. Format didukung: {', '.join(SUPPORTED_FORMATS)}"
            )
            return

        await ctx.send("📥 Mengunduh file video dari Discord...")

        # Simpan ke temp folder
        temp_input_dir = config.TEMP_DIR / "discord_uploads"
        temp_input_dir.mkdir(exist_ok=True)
        file_path = temp_input_dir / f"input_{ctx.message.id}{ext}"
        await attachment.save(str(file_path))

        await ctx.send("✅ File berhasil diunduh. Menambahkan pekerjaan ke antrean...")

    # Cek jika tidak ada URL maupun file attachment
    if not url and not file_path:
        await ctx.send("❌ Harap masukkan URL YouTube atau unggah file video!")
        return

    # Tambahkan job ke database
    job_id = db.add_job(
        url=url,
        file_path=str(file_path) if file_path else None,
        content_type=content_type,
        max_clips=max_clips,
        lang=lang,
        no_face_track=False,
        discord_channel_id=ctx.channel.id,
    )

    # Dapatkan status antrean
    status = db.get_queue_status()
    queue_pos = status["pending"]

    await ctx.send(
        f"⏳ **Pekerjaan #{job_id} ditambahkan ke antrean.**\n"
        f"Posisi antrean saat ini: **{queue_pos}**. Silakan tunggu giliran Anda."
    )


# Worker loop untuk menjalankan pemrosesan video secara berurutan
@tasks.loop(seconds=10)
async def worker_loop():
    # Periksa apakah ada job yang sedang berjalan
    status = db.get_queue_status()
    if status["processing"] > 0:
        return  # Hanya proses satu video dalam satu waktu

    # Ambil job pending berikutnya
    job = db.get_next_pending_job()
    if not job:
        return  # Tidak ada antrean

    job_id = job["id"]
    channel_id = job["discord_channel_id"]
    channel = bot.get_channel(channel_id)

    if channel:
        await channel.send(f"⚙️ **Pekerjaan #{job_id} mulai diproses...**")

    # Update status ke processing
    db.update_job_status(job_id, "processing")

    # Buat output folder unik untuk job ini
    job_output_dir = config.OUTPUT_DIR / f"job_{job_id}"
    job_output_dir.mkdir(parents=True, exist_ok=True)

    # Siapkan argumen baris perintah untuk subprocess main.py
    cmd_args = []
    if job["url"]:
        cmd_args.extend(["--url", job["url"]])
    elif job["file_path"]:
        cmd_args.extend(["--file", job["file_path"]])

    cmd_args.extend([
        "--type",
        job["content_type"],
        "--max-clips",
        str(job["max_clips"]),
        "--output-dir",
        str(job_output_dir),
    ])

    if job["lang"]:
        cmd_args.extend(["--lang", job["lang"]])
    else:
        cmd_args.extend(["--lang", "None"])

    # Jalankan main.py sebagai subprocess asinkron
    print(f"Running job #{job_id}: main.py with args {cmd_args}")
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "main.py",
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # Sukses
            db.update_job_status(job_id, "completed")
            if channel:
                await channel.send(
                    f"✅ **Pekerjaan #{job_id} sukses!** Mengunggah klip hasil..."
                )

                # Cari klip di folder output
                clips = list(job_output_dir.glob("*.mp4"))
                if not clips:
                    await channel.send("⚠ Tidak ada klip video yang dihasilkan.")
                else:
                    for clip in sorted(clips):
                        # Cek ukuran file
                        file_size_mb = clip.stat().st_size / (1024 * 1024)
                        if file_size_mb > 24.5:  # Batas aman Discord free upload (25MB)
                            await channel.send(
                                f"📹 **{clip.name}** ({file_size_mb:.1f} MB) terlalu besar untuk diunggah langsung ke Discord. "
                                "File tersimpan di VPS."
                            )
                        else:
                            await channel.send(
                                content=f"📹 **{clip.name}** ({file_size_mb:.1f} MB):",
                                file=discord.File(str(clip)),
                            )
        else:
            # Gagal
            err_msg = stderr.decode(errors="ignore").strip()
            print(
                f"Job #{job_id} failed with exit code {process.returncode}. Error:\n{err_msg}"
            )
            db.update_job_status(job_id, "failed", error_message=err_msg)
            if channel:
                await channel.send(
                    f"❌ **Pekerjaan #{job_id} gagal!**\n"
                    f"Error code: `{process.returncode}`\n"
                    f"Pesan Error (200 karakter pertama): ```\n{err_msg[:200]}...\n```"
                )
    except Exception as e:
        print(f"Exception during job #{job_id} processing: {e}")
        db.update_job_status(job_id, "failed", error_message=str(e))
        if channel:
            await channel.send(
                f"❌ **Pekerjaan #{job_id} mengalami error sistem:** `{e}`"
            )
    finally:
        # Hapus folder output unik untuk job ini agar hemat space VPS
        if job_output_dir.exists():
            shutil.rmtree(str(job_output_dir))

        # Hapus file input lokal jika didownload dari Discord attachment
        if job["file_path"] and Path(job["file_path"]).exists():
            try:
                os.remove(job["file_path"])
            except Exception as e:
                print(f"Failed to remove uploaded file {job['file_path']}: {e}")


if __name__ == "__main__":
    if not config.DISCORD_BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN tidak ditemukan di file .env!")
        sys.exit(1)

    bot.run(config.DISCORD_BOT_TOKEN)
