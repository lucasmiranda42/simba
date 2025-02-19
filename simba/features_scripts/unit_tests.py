import pandas as pd
from pathlib import Path
import os


def read_video_info(vid_info_df: pd.DataFrame,
                    video_name: str):
    """
    Helper to read the meta data (pixels per mm, resolution, fps etc) from the video_info.csv for a single input file

    Parameters
    ----------
    vid_info_df: pd.DataFrame
        Pandas dataframe representing the content of the project_folder/logs/video_info.csv of the SimBA project.
    video_name: str
        The name of the video without extension to get the meta data for.

    Returns
    -------
    video_settings: pd.DataFrame
    px_per_mm: float
    fps: float
    """

    video_settings = vid_info_df.loc[vid_info_df['Video'] == video_name]
    if len(video_settings) > 1:
        print(
            'SIMBA ERROR: SimBA found multiple rows in the project_folder/logs/video_info.csv named {}. Please make sure that each video is represented once only in the video_info.csv'.format(
                str(video_name)))
        raise ValueError(
            'SIMBA ERROR: SimBA found multiple rows in the project_folder/logs/video_info.csv named {}. Please make sure that each video is represented once only in the video_info.csv'.format(
                str(video_name)))
    elif len(video_settings) < 1:
        print(
            'Error: make sure all the videos that are going to be analyzed are represented in the project_folder/logs/video_info.csv file. SimBA could not find {} in the video_info.csv table.'.format(
                str(video_name)))
        raise ValueError(
            'Error: make sure all the videos that are going to be analyzed are represented in the project_folder/logs/video_info.csv file. SimBA could not find {} in the video_info.csv table.'.format(
                str(video_name)))
    else:
        try:
            px_per_mm = float(video_settings['pixels/mm'])
            fps = float(video_settings['fps'])
            return video_settings, px_per_mm, fps
        except TypeError:
            print(
                'SIMBA ERROR: make sure all the videos that are going to be analyzed are represented with appropriate values in the project_folder/logs/video_info.csv file in the SimBA project')
            raise ValueError(
                'SIMBA ERROR: make sure all the videos that are going to be analyzed are represented with appropriate values in the project_folder/logs/video_info.csv file in the SimBA project')


def check_minimum_roll_windows(roll_windows_values: list,
                               minimum_fps: float):

    """
    Helper to remove any rolling temporal window that are shorter than a single frame in
    any of the videos in the project.

    Parameters
    ----------
    roll_windows_values: list
        List of rolling temporal windows represented as frame counts. E.g., [10, 15, 30, 60]
    minimum_fps: float
        The lowest fps of the videos that are to be analyzed. E.g., 10

    Returns
    -------
    roll_windows_values: list
    """

    for win in range(len(roll_windows_values)):
        if minimum_fps < roll_windows_values[win]:
            roll_windows_values[win] = minimum_fps
        else:
            pass
    roll_windows_values = list(set(roll_windows_values))
    return roll_windows_values


def check_if_file_exist(file_path: str):
    """
    Helper to check if a file exist.
    Parameters
    ----------
    file_path: str

    Returns
    -------
    bool
    """

    path_file_path = Path(file_path)
    if path_file_path.is_file():
        return True
    else:
        return False


def check_if_file_is_readable(file_path: str):
    """
    Helper to check if a file is readable.
    Parameters
    ----------
    file_path: str

    Returns
    -------
    bool
    """
    if os.access(file_path, os.R_OK):
        return True
    else:
        return False


def read_video_info_csv(file_path: str):
    """
    Helper to read the project_folder/logs/video_info.csv of the SimBA project in as a pd.DataFrame
    Parameters
    ----------
    file_path: str

    Returns
    -------
    info_df: pd.DataFrame
    """

    if not check_if_file_exist(file_path):
        print(
            'The project "project_folder/logs/video_info.csv" file does not exists. Please generate the file by completing the [Video parameters] step')
        raise FileNotFoundError
    if not check_if_file_is_readable(file_path):
        print(
            'The project "project_folder/logs/video_info.csv" file does not readable/corrupted. Please re-create it by completing the [Video parameters] step')
        raise ValueError
    info_df = pd.read_csv(file_path)
    for c in ['Video', 'fps', 'Resolution_width', 'Resolution_height', 'Distance_in_mm', 'pixels/mm']:
        if c not in info_df.columns:
            print(
                'The project "project_folder/logs/video_info.csv" does not not have an anticipated {} header. Please re-create the file and make sure each video has a {} value'.format(
                    str(c), str(c)))
            raise ValueError
    info_df['Video'] = info_df['Video'].astype(str)
    for c in ['fps', 'Resolution_width', 'Resolution_height', 'Distance_in_mm', 'pixels/mm']:
        try:
            info_df[c] = info_df[c].astype(float)
        except:
            print(
                'One or more values in the {} column of the "project_folder/logs/video_info.csv" file could not be interepreted as a number. Please re-create the file and make sure the entries in the {} column are all numeric.'.format(
                    str(c), str(c)))
            raise ValueError
    if info_df['fps'].min() <= 1:
        print(
            'SIMBA WARNING: Videos in your SimBA project have an FPS of 1 or less. Please use videos with more than one frame per second, or correct the inaccurate fps inside the `project_folder/logs/videos_info.csv` file')

    return info_df
