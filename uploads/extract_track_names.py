import argparse
import os
import re


def generate_tracklist_file(album_folder_path):
    """
    Generate an output file containing album data

    First line : album folder
    Rest: 1 track name per line, including file extension

    Output: a file named album_folder
    """
    if not os.path.isdir(album_folder_path):
        return False
    track_names = []

    current_folder = os.path.dirname(os.path.realpath(__file__))
    target = os.path.join(current_folder, 'track_files')
    os.makedirs(target, exist_ok=True)

    for (_, _, filenames) in os.walk(album_folder_path):
        track_names.extend([audio_file for audio_file in filenames if os.path.splitext(audio_file)[1] in ['.flac','.mp3']])
      
    formated_tracks = map(format_tracknames, track_names)
    parent_folder = os.path.basename(os.path.dirname(album_folder_path))
    out_filebase= remove_paranthesis(parent_folder)
    out_filename= os.path.join(target, out_filebase + ".txt")

    with open(out_filename, "+w") as output:
        output.write(out_filebase.replace('-', ' ').replace('.', ' ') + "\n")
        output.writelines(sorted(formated_tracks))


def remove_paranthesis(name):
    """
    Remove paranthesis from a track name
    """
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s*\[[^\]]*\]", "", name)
    return name


def format_tracknames(track_name):
    """
    Apply format rules to a track name

    Template: 01-Track_name_with_underscore.flac
    - 1st char after the number will be set to "-"
    - replace spaces with "_"
    - remove (Paranthesis) inside of trackname
    """
    format_template = r"^(?P<nr>0*\d+)(?P<sep>[.-]+)(?P<name>.+?)(?P<ext>\.(?:flac|mp3))$"
    regx = re.compile(format_template, re.IGNORECASE)
    match = regx.match(track_name)
    if not match:
        return None
    
    formatted_name = remove_paranthesis(match.group("name").replace(" ", "_").replace(".","")).strip('_')
    formatted_name = match.group("nr") + "-" + formatted_name + match.group("ext").lower() + "\n"

    return formatted_name


def generate_files(filename):
    """Reads a file containing paths and generates output files
    
    Returns a list of paths that could not be processed
    """
    
    with open(filename, "r") as file_of_paths:
        paths = file_of_paths.readlines()
        not_found = []
        for each_path in paths:
            stripped_path = each_path.strip('\n')
            if os.path.isdir(stripped_path):
                generate_tracklist_file(stripped_path)
            else:
                not_found.append(each_path)
    return not_found


def validate_filename(value):
    return value if os.path.isfile(value) else None


def validate_path(value):
    return value if os.path.isdir(value) else None


def get_args():
    """ Generates the args parser and returns the arguments"""

    parser = argparse.ArgumentParser(
        prog="GenInputFiles",
        description="Generates album files, to be imported in wcddb",
        usage='%(prog) [options]'
    )
    parser.add_argument('-f', '--filename',
                        help='Filename containing list of folders to be processed',
                        type=validate_filename)
    parser.add_argument('-p', '--path',
                        help='Path of existing folder',
                        type=validate_path)

    arguments = parser.parse_args()


    return arguments.filename, arguments.path


if __name__ == "__main__":
    filename, folder_path = get_args()
    print(filename, folder_path)
    if filename is not None and folder_path is not None:
        print('No options defined. Use -f OR -p')
    elif filename is not None:
        print(f"Generating output files based on input file {filename}")
        not_generated = generate_files(filename)
        print(f'Not generated output files for :\n {not_generated}')
    elif folder_path is not None:
        print(f"Generating output file based on input folder {folder_path}")
        generate_tracklist_file(folder_path)
    else:
        print("No files generated. Check arguments")
    


