import os
import re
from datetime import datetime, timezone
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
import yaml

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

            if singer_name and not existing_singer_id:
                singer = Singer.query.filter_by(name=singer_name).first()
                if singer is None:
                    singer = Singer(name=singer_name)
                    db.session.add(singer)
                    db.session.flush()
            elif existing_singer_id and not singer_name:
                singer = Singer.query.get(existing_singer_id)
            else:
                flash("Please enter a new Artist or choose an existing. Both not accepted", "error")
                return redirect(url_for("config"))

            try:
                album_name, tracks = parse_import_file(upload)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("config"))

            existing_album = Album.query.filter(db.func.lower(Album.name) == album_name.lower()).first()
            if existing_album is not None:
                flash("Album already exists in the database.", "error")
                return redirect(url_for("config", artist_id=singer.id))

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

        if action == "export_data":
            export_payload = build_export_payload()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            export_filename = f"collection_export_{timestamp}.yaml"
            export_path = os.path.join(app.config["UPLOAD_FOLDER"], export_filename)

            with open(export_path, "w", encoding="utf-8") as export_file:
                yaml.safe_dump(export_payload, export_file, sort_keys=False)

            flash("Data exported successfully.", "success")
            return send_file(
                export_path,
                as_attachment=True,
                download_name=export_filename,
                mimetype="application/x-yaml",
            )

        if action == "import_data":
            import_file = request.files.get("import_file")
            if not import_file or import_file.filename == "":
                flash("Please select a JSON file to import.", "error")
                return redirect(url_for("config"))

            if not import_file.filename.lower().endswith((".yaml", ".yml")):
                flash("Please select a .yaml or .yml file.", "error")
                return redirect(url_for("config"))

            try:
                payload = yaml.safe_load(import_file.stream)
            except (TypeError, ValueError, UnicodeDecodeError) as exc:
                flash(f"Invalid YAML file: {exc}", "error")
                return redirect(url_for("config"))

            try:
                db.session.rollback()
                validate_import_payload(payload)
                import_database_from_payload(payload)
                db.session.commit()
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("config"))
            except Exception as exc:
                db.session.rollback()
                flash(f"Import failed: {exc}", "error")
                return redirect(url_for("config"))

            flash("Data imported successfully.", "success")
            return redirect(url_for("config"))

    return render_template(
        "config.html",
        singers=singers,
        selected_singer=selected_singer,
        albums=albums,
    )


def build_export_payload():
    singers = Singer.query.order_by(Singer.name).all()
    payload = {"singers": []}

    for singer in singers:
        payload["singers"].append(
            {
                "name": singer.name,
                "albums": [
                    {
                        "name": album.name,
                        "tracks": [
                            {
                                "name": track.name,
                                "track_number": track.track_number,
                            }
                            for track in sorted(album.tracks, key=lambda item: item.track_number)
                        ],
                    }
                    for album in sorted(singer.albums, key=lambda item: item.name)
                ],
            }
        )

    return payload


def validate_import_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Import file must contain a JSON object.")

    singers = payload.get("singers")
    if not isinstance(singers, list):
        raise ValueError("Import file must contain a 'singers' list.")

    seen_singer_names = set()
    for singer_index, singer_data in enumerate(singers):
        if not isinstance(singer_data, dict):
            raise ValueError(f"Singer entry {singer_index + 1} must be an object.")

        singer_name = singer_data.get("name")
        if not isinstance(singer_name, str) or not singer_name.strip():
            raise ValueError(f"Singer entry {singer_index + 1} is missing a valid name.")

        normalized_singer_name = singer_name.strip()
        if normalized_singer_name in seen_singer_names:
            raise ValueError("Import contains duplicate singer names.")
        seen_singer_names.add(normalized_singer_name)

        albums = singer_data.get("albums")
        if not isinstance(albums, list):
            raise ValueError(f"Singer '{normalized_singer_name}' must contain an 'albums' list.")

        seen_album_names = set()
        for album_index, album_data in enumerate(albums):
            if not isinstance(album_data, dict):
                raise ValueError(f"Album entry {album_index + 1} for singer '{normalized_singer_name}' must be an object.")

            album_name = album_data.get("name")
            if not isinstance(album_name, str) or not album_name.strip():
                raise ValueError(f"Album entry {album_index + 1} for singer '{normalized_singer_name}' is missing a valid name.")

            normalized_album_name = album_name.strip()
            if normalized_album_name in seen_album_names:
                raise ValueError(f"Singer '{normalized_singer_name}' contains duplicate album names.")
            seen_album_names.add(normalized_album_name)

            tracks = album_data.get("tracks")
            if not isinstance(tracks, list):
                raise ValueError(f"Album '{normalized_album_name}' must contain a 'tracks' list.")

            seen_track_numbers = set()
            for track_index, track_data in enumerate(tracks):
                if not isinstance(track_data, dict):
                    raise ValueError(f"Track entry {track_index + 1} for album '{normalized_album_name}' must be an object.")

                track_name = track_data.get("name")
                track_number = track_data.get("track_number")
                if not isinstance(track_name, str) or not track_name.strip():
                    raise ValueError(f"Track entry {track_index + 1} for album '{normalized_album_name}' is missing a valid name.")
                if not isinstance(track_number, int) or isinstance(track_number, bool) or track_number < 1:
                    raise ValueError(f"Track entry {track_index + 1} for album '{normalized_album_name}' has an invalid track number.")
                if track_number in seen_track_numbers:
                    raise ValueError(f"Album '{normalized_album_name}' contains duplicate track numbers.")
                seen_track_numbers.add(track_number)


def import_database_from_payload(payload):
    Track.query.delete(synchronize_session=False)
    Album.query.delete(synchronize_session=False)
    Singer.query.delete(synchronize_session=False)

    for singer_data in payload["singers"]:
        singer = Singer(name=singer_data["name"].strip())
        db.session.add(singer)
        db.session.flush()

        for album_data in singer_data["albums"]:
            album = Album(name=album_data["name"].strip(), singer=singer)
            db.session.add(album)
            db.session.flush()

            for track_data in album_data["tracks"]:
                db.session.add(
                    Track(
                        name=track_data["name"].strip(),
                        track_number=track_data["track_number"],
                        album=album,
                    )
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
        match = re.match(r'^0*([0-9]+)[-_](.+?)\.[^.]+$', line)
        if match:
            number_text = int(match.group(1))
            title = match.group(2).replace('_', ' ').capitalize()
            tracks.append((int(number_text), title))

    if not tracks:
        raise ValueError("No track entries were found in the file.")

    return album_name, tracks


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
