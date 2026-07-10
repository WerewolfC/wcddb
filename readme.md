# 🎵 Audio CD Collection Manager (Flask App)

## Overview

This application is a web-based CD collection manager built with **Python**, using the Flask framework and SQLAlchemy for database interaction.

It allows you to:

* Browse all **artists (singers)** from the landing page
* View all albums and tracks for a selected artist
* Add new artists and albums
* Import album tracklists from a structured text file
* Remove existing artists and albums

---

## 🧱 Tech Stack

* **Backend Framework**: Flask
* **Database**: SQLite
* **ORM**: SQLAlchemy
* **Frontend**: HTML (Jinja2 templates), basic CSS, use dark scheme
* **File Uploads**: Flask file handling

---

## 📂 Project Structure

```id="proj123"
project/
│
├── app.py
├── models.py
├── templates/
│   ├── base.html
│   ├── index.html          # landing page (artists list)
│   ├── artist.html         # albums + tracks for one artist
│   ├── config.html         # add/remove page
│
├── static/
└── uploads/
```

---

## 🗄️ Database Schema

### Singer

* `id` (Integer, Primary Key)
* `name` (String, unique)

### Album

* `id` (Integer, Primary Key)
* `name` (String)
* `singer_id` (Foreign Key → Singer.id)

### Track

* `id` (Integer, Primary Key)
* `name` (String)
* `track_number` (Integer)
* `album_id` (Foreign Key → Album.id)

---

## 🏠 Landing Page (Artists List)

### Route

`/`

### Features

* Displays all artists in the database
* Each artist is clickable
* Includes a link to the **Configuration Page**

### Behavior

* Query all artists
* Render as a list:

```id="artists_list"
Artist 1
Artist 2
Artist 3
```

* Clicking an artist redirects to:

```
/artist/<artist_id>
```

---

## 🎤 Artist Page (Albums & Tracks)

### Route

`/artist/<id>`

### Features

* Displays:

  * Artist name
  * All albums for that artist
  * Tracks for each album (ordered)

### Example Output

```id="artist_view"
Artist: X

Album: A
  1. Song 1
  2. Song 2

Album: B
  1. Song 3
```

---

## ⚙️ Configuration Page

### Route

`/config`

### Features

This page contains **two main sections**:

---

### ➕ Add Artists / Albums

#### Controls

* Input field for **new artist name**
* Dropdown for **existing artists**
* File upload (`.txt`) for album import

#### Behavior

* If a new artist name is provided → create artist
* Otherwise → use selected artist
* Upload file → parse and create album + tracks

---

### 📥 File Import Format

```id="file_format"
Album Name
01_Song One.mp3
02_Song Two.mp3
03_Another Song.mp3
```

#### Rules

* First line = album name
* Remaining lines:

  * Format: `<track_number>_<song_title>`
  * File extension ignored

---

### ⚙️ Import Logic

```python id="import_logic"
lines = file.read().decode("utf-8").splitlines()

album_name = lines[0]
tracks = lines[1:]

for line in tracks:
    number, rest = line.split("_", 1)
    title = rest.rsplit(".", 1)[0]
```

---

### ❌ Remove Artists / Albums

#### Controls

* Select the artist from a drop-down list
* After artist is selected, display the list of albums,
  - each album has its own delete button
  - delete is being executing after confirmation (yes/no) new window gui 
* There should be a delete Artist button after the albums list

#### Behavior

* Deleting an **album** removes all its tracks
* Deleting a **singer** can be executed ONLY if there are no albums allocated to it



---

## 🔄 Workflow

### Browsing

1. Open `/`
2. See all artists
3. Click an artist
4. View albums and tracks

---

### Adding an Album

1. Go to `/config`
2. In **Add section**:

   * Select existing artist OR enter new one
3. Upload `.txt` file
4. Submit → album is created

---

### Removing Data

1. Go to `/config`
2. In **Remove section**:

   * Choose artist or album
3. Click delete
4. Data is removed (with cascading behavior)

---

## 🔗 Navigation

* Landing page includes link to `/config`
* Configuration page should include link back to `/`

---

* create a requirements.txt with all required pyhon modules so it could be imported by pip
---

## ✅ Summary

This application provides a clean and simple backend:

* Flask handles routing and UI
* SQLAlchemy manages relational data
* SQLite stores your CD collection
* File import simplifies adding albums
* Configuration page centralizes all management (add/remove)

The design is minimal, structured, and tailored for personal collection management.

---
