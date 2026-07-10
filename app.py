import os
from flask import Flask, flash, redirect, render_template, request, url_for

from models import Album, Singer, Track, db, init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///collection.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

with app.app_context():
    init_db()


@app.route("/")
def index():
    singers = Singer.query.order_by(Singer.name).all()
    return render_template("index.html", singers=singers)


@app.route("/artist/<int:singer_id>")
def artist_detail(singer_id: int):
    singer = Singer.query.get_or_404(singer_id)
    albums = Album.query.filter_by(singer_id=singer_id).order_by(Album.name).all()
    return render_template("artist.html", singer=singer, albums=albums)


@app.route("/config", methods=["GET", "POST"])
def config():
    singers = Singer.query.order_by(Singer.name).all()
    selected_singer_id = request.args.get("artist_id", type=int)
    selected_singer = Singer.query.get(selected_singer_id) if selected_singer_id else None
    albums = (
        Album.query.filter_by(singer_id=selected_singer_id).order_by(Album.name).all()
        if selected_singer_id
        else []
    )

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            singer_name = request.form.get("new_singer", "").strip()
            existing_singer_id = request.form.get("existing_singer", "", type=int)
            upload = request.files.get("track_file")

            if not upload or upload.filename == "":
                flash("Please upload a tracklist file.", "error")
                return redirect(url_for("config"))

            if singer_name:
                singer = Singer.query.filter_by(name=singer_name).first()
                if singer is None:
                    singer = Singer(name=singer_name)
                    db.session.add(singer)
                    db.session.flush()
            elif existing_singer_id:
                singer = Singer.query.get(existing_singer_id)
            else:
                flash("Please enter a new singer name or choose an existing singer.", "error")
                return redirect(url_for("config"))

            try:
                album_name, tracks = parse_import_file(upload)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("config"))

            album = Album(name=album_name, singer=singer)
            db.session.add(album)
            db.session.flush()

            for track_number, track_name in tracks:
                db.session.add(Track(name=track_name, track_number=track_number, album=album))

            db.session.commit()
            flash("Album imported successfully.", "success")
            return redirect(url_for("config", artist_id=singer.id))

        if action == "delete_album":
            album_id = request.form.get("album_id", type=int)
            album = Album.query.get(album_id)
            if album is None:
                flash("Album not found.", "error")
            else:
                singer_id = album.singer_id
                db.session.delete(album)
                db.session.commit()
                flash("Album removed.", "success")
                return redirect(url_for("config", artist_id=singer_id))

        if action == "delete_singer":
            singer_id = request.form.get("singer_id", type=int)
            singer = Singer.query.get(singer_id)
            if singer is None:
                flash("Singer not found.", "error")
            elif singer.albums:
                flash("Singer cannot be deleted while albums still exist.", "error")
            else:
                db.session.delete(singer)
                db.session.commit()
                flash("Singer removed.", "success")
                return redirect(url_for("config"))

    return render_template(
        "config.html",
        singers=singers,
        selected_singer=selected_singer,
        albums=albums,
    )


def parse_import_file(upload_file):
    content = upload_file.read().decode("utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    if not lines:
        raise ValueError("The uploaded file is empty.")

    album_name = lines[0]
    tracks = []

    for line in lines[1:]:
        if "_" not in line:
            continue
        number_text, rest = line.split("_", 1)
        title = rest.rsplit(".", 1)[0]
        tracks.append((int(number_text), title))

    if not tracks:
        raise ValueError("No track entries were found in the file.")

    return album_name, tracks


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
