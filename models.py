from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Singer(db.Model):
    __tablename__ = "singers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    albums = db.relationship("Album", back_populates="singer", cascade="all, delete-orphan")


class Album(db.Model):
    __tablename__ = "albums"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    singer_id = db.Column(db.Integer, db.ForeignKey("singers.id"), nullable=False)

    singer = db.relationship("Singer", back_populates="albums")
    tracks = db.relationship("Track", back_populates="album", cascade="all, delete-orphan")


class Track(db.Model):
    __tablename__ = "tracks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    track_number = db.Column(db.Integer, nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)

    album = db.relationship("Album", back_populates="tracks")


def init_db():
    db.create_all()
