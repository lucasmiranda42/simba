__author__ = "Simon Nilsson", "JJ Choong"

import time

import cv2
import pandas as pd
from simba.rw_dfs import read_df, save_df
from simba.read_config_unit_tests import (read_config_entry,
                                          read_config_file,
                                          check_file_exist_and_readable,
                                          check_int,
                                          check_float)
from simba.misc_tools import get_video_meta_data, get_fn_ext
import simba
from tkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
from subprocess import Popen, PIPE
from copy import deepcopy
import os
from simba.train_model_functions import get_all_clf_names

class LabellingInterface(object):
    """
    Class for launching ``standard`` and ``pseudo``-labelling (annotation) GUI interface in SimBA.

    Parameters
    ----------
    config_path: str
        path to SimBA project config file in Configparser format
    file_path: str
        Path to video that is to be annotated
    setting: str
        String representing annotation method. OPTIONS: 'from_scratch' or 'pseudo'
    threshold_dict: dict
        If setting is ``pseudo``, threshold_dict dict contains the machine probability thresholds, with the classifier
        names as keys and the classification probabilities as values, e.g. {'Attack': 0.40, 'Sniffing': 0.7).
    continuing: bool
        If True, continouing previously started annotation session.


    Notes
    ----------
    `Annotation tutorial <https://github.com/sgoldenlab/simba/blob/master/docs/label_behavior.md>`__.

    Examples
    ----------
    >>> select_labelling_video(config_path='MyConfigPath', threshold_dict={'Attack': 0.4}, file_path='MyVideoFilePath', setting='pseudo', continuing=False)
    """

    def __init__(self,
                 config_path: str=None,
                 file_path: str=None,
                 setting: str = 'pseudo',  # from_scratch, #pseudo
                 threshold_dict: dict=None,
                 continuing: bool=False):

        self.padding, self.file_path = 5, file_path
        self.frm_no, self.threshold_dict = 0, threshold_dict
        self.config_path, self.setting = config_path, setting
        self.config = read_config_file(config_path)
        self.play_video_script_path = os.path.join(os.path.dirname(simba.__file__), 'play_video_pseudo.py')
        self.file_type = read_config_entry(self.config, 'General settings', 'workflow_file_type', 'str', 'csv')
        self.target_cnt = read_config_entry(self.config, 'SML settings', 'no_targets', 'int')
        self.project_path = read_config_entry(self.config, 'General settings', 'project_path', data_type='str')
        self.videos_dir_path = os.path.join(self.project_path, 'videos')
        _, self.video_name, _ = get_fn_ext(filepath=file_path)
        self.features_extracted_folder = os.path.join(self.project_path, 'csv', 'features_extracted')
        self.targets_inserted_folder = os.path.join(self.project_path, 'csv', 'targets_inserted')
        self.machine_results_folder = os.path.join(self.project_path, 'csv', 'machine_results')
        self.features_extracted_file_path = os.path.join(self.features_extracted_folder, self.video_name + '.' + self.file_type)
        self.targets_inserted_file_path = os.path.join(self.targets_inserted_folder, self.video_name + '.' + self.file_type)
        self.machine_results_file_path = os.path.join(self.machine_results_folder, self.video_name + '.' + self.file_type)
        self.video_path = file_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.video_meta_data = get_video_meta_data(video_path=self.video_path)
        self.frame_lst = list(range(0, self.video_meta_data['frame_count']))
        self.max_frm_no = max(self.frame_lst)
        self.target_lst = get_all_clf_names(config=self.config, target_cnt=self.target_cnt)
        self.max_frm_size = 1080, 650
        self.main_window = Toplevel()
        if continuing:
            check_file_exist_and_readable(file_path=self.targets_inserted_file_path)
            check_file_exist_and_readable(file_path=self.features_extracted_file_path)
            self.data_df = read_df(self.targets_inserted_file_path, self.file_type)
            self.data_df_features = read_df(self.features_extracted_file_path, self.file_type)
            missing_idx = self.data_df_features.index.difference(self.data_df.index)
            if len(missing_idx) > 0:
                self.data_df_features = self.data_df_features.iloc[self.data_df_features.index.difference(self.data_df.index)]
                self.data_df = pd.concat([self.data_df, self.data_df_features], axis=0).sort_index()
            self.main_window.title('SIMBA ANNOTATION INTERFACE (CONTINUING ANNOTATIONS) - {}'.format(self.video_name))
            try:
                self.frm_no = read_config_entry(self.config, 'Last saved frames', self.video_name, data_type='int')
            except ValueError:
                pass
        else:
            if setting == 'from_scratch':
                check_file_exist_and_readable(file_path=self.features_extracted_file_path)
                self.data_df = read_df(self.features_extracted_file_path, self.file_type)
                self.main_window.title('SIMBA ANNOTATION INTERFACE (ANNOTATING FROM SCRATCH) - {}'.format(self.video_name))
                for target in self.target_lst:
                    self.data_df[target] = 0
            elif setting == 'pseudo':
                check_file_exist_and_readable(file_path=self.machine_results_file_path)
                self.data_df = read_df(self.machine_results_file_path, self.file_type)
                for target in self.target_lst:
                    self.data_df.loc[self.data_df['Probability_{}'.format(target)] > self.threshold_dict[target], target] = 1
                    self.data_df.loc[self.data_df['Probability_{}'.format(target)] <= self.threshold_dict[target], target] = 0
                self.main_window.title('SIMBA ANNOTATION INTERFACE (PSEUDO-LABELLING) - {}'.format(self.video_name))
        self.data_df_targets = self.data_df[self.target_lst]
        self.folder = Frame(self.main_window)
        self.buttons_frm = Frame(self.main_window, bd=2, width=700, height=300)
        self.current_frm_n = IntVar(self.main_window, value=self.frm_no)
        self.change_frm_box = Entry(self.buttons_frm, width=7, textvariable=self.current_frm_n)
        self.frame_number_lbl = Label(self.buttons_frm, text="Frame number")
        self.forward_btn = Button(self.buttons_frm, text=">", command=lambda: self.__advance_frame(new_frm_number=int(self.current_frm_n.get() + 1)))
        self.backward_btn = Button(self.buttons_frm, text="<", command=lambda: self.__advance_frame(new_frm_number=int(self.current_frm_n.get() - 1)))
        self.forward_max_btn = Button(self.buttons_frm, text=">>", command=lambda: self.__advance_frame(len(self.frame_lst) - 1))
        self.backward_max_btn = Button(self.buttons_frm, text="<<", command=lambda: self.__advance_frame(0))
        self.select_frm_btn = Button(self.buttons_frm, text="Jump to selected frame", command=lambda: self.__advance_frame(new_frm_number=int(self.change_frm_box.get())))
        self.jump_frame = Frame(self.main_window)
        self.jump = Label(self.jump_frame, text="Jump Size:")
        self.jump_size = Scale(self.jump_frame, from_=0, to=100, orient=HORIZONTAL, length=200)
        self.jump_size.set(0)
        self.jump_back = Button(self.jump_frame, text="<<",command=lambda: self.__advance_frame(int(self.change_frm_box.get()) - self.jump_size.get()))
        self.jump_forward = Button(self.jump_frame, text=">>", command=lambda: self.__advance_frame(int(self.change_frm_box.get()) + self.jump_size.get()))

        self.folder.grid(row=0, column=1, sticky=N)
        self.buttons_frm.grid(row=1, column=0)
        self.change_frm_box.grid(row=0, column=1)
        self.forward_btn.grid(row=1, column=3, sticky=E, padx=self.padding)
        self.backward_btn.grid(row=1, column=1, sticky=W, padx=self.padding)
        self.change_frm_box.grid(row=1, column=1)
        self.forward_max_btn.grid(row=1, column=4, sticky=W, padx=self.padding)
        self.backward_max_btn.grid(row=1, column=0, sticky=W, padx=self.padding)
        self.select_frm_btn.grid(row=2, column=1, sticky=N)
        self.jump_frame.grid(row=2, column=0)
        self.jump.grid(row=0, column=0, sticky=W)
        self.jump_size.grid(row=0, column=1, sticky=W)
        self.jump_back.grid(row=0, column=2, sticky=E)
        self.jump_forward.grid(row=0, column=3, sticky=W)

        ## Behavior Checkbox
        self.check_frame = Frame(self.main_window, bd=2, width=300, height=500)
        self.check_frame.grid(row=0, column=1)
        self.check_behavior_lbl = Label(self.check_frame, text="Check Behavior:")
        self.check_behavior_lbl.config(font=("Calibri", 16))
        self.check_behavior_lbl.grid(sticky=N)

        self.checkboxes = {}
        for target_cnt, target in enumerate(self.target_lst):
            self.checkboxes[target] = {}
            self.checkboxes[target]['name'] = target
            self.checkboxes[target]['var'] = IntVar()
            self.checkboxes[target]['cb'] = Checkbutton(self.check_frame, text=target, variable=self.checkboxes[target]['var'], command=lambda k=self.checkboxes[target]['name']: self.save_behavior_in_frm(frame_number=int(self.current_frm_n.get()), target=k))
            self.checkboxes[target]['cb'].grid(row=target_cnt + 1, sticky=W)
            self.checkboxes[target]['var'].set(self.data_df_targets[target].iloc[self.current_frm_n.get()])

        self.range_on = IntVar(value=0)
        self.range_frames = Frame(self.main_window)
        self.range_frames.grid(row=1, column=1, sticky=S)
        self.select_range = Checkbutton(self.range_frames, text='Frame range', variable=self.range_on)
        self.select_range.grid(row=0, column=0, sticky=W)
        self.first_frame = Entry(self.range_frames, width=7)
        self.first_frame.grid(row=0, column=1, sticky=E)
        self.to_label = Label(self.range_frames, text=" to ")
        self.to_label.grid(row=0, column=2, sticky=E)
        self.last_frame = Entry(self.range_frames, width=7)
        self.last_frame.grid(row=0, column=3, sticky=E)

        save = Button(self.main_window, text="Save Range", command=lambda: self.__save_behavior_in_range(self.first_frame.get(),self.last_frame.get()))
        save.grid(row=2, column=1, sticky=N)

        self.generate = Button(self.main_window, text="Save Annotations", command=lambda: self.__save_results(), fg='blue')
        self.generate.config(font=("Calibri", 16))
        self.generate.grid(row=10, column=1, sticky=N)

        self.video_player_frm = Frame(self.main_window, width=100, height=100)
        self.video_player_frm.grid(row=0, column=2, sticky=N)
        self.play_video_btn = Button(self.video_player_frm, text='Open Video', command=self.__play_video)
        self.play_video_btn.grid(sticky=N, pady=10)
        self.video_key_lbls = Label(self.video_player_frm, text='\n\n  Keyboard shortcuts for video navigation: \n p = Pause/Play'
                                             '\n\n After pressing pause:'
                                             '\n o = +2 frames \n e = +10 frames \n w = +1 second'
                                             '\n\n t = -2 frames \n s = -10 frames \n x = -1 second'
                                             '\n\n q = Close video window \n\n')
        self.video_key_lbls.grid(sticky=W)
        self.update_img_from_video = Button(self.video_player_frm, text='Show current video frame', command=self.__update_frame_from_video)
        self.update_img_from_video.grid(sticky=N)
        self.__bind_shortcut_keys()
        self.key_presses_lbl = Label(self.video_player_frm,
                            text='\n\n Keyboard shortcuts for frame navigation: \n Right Arrow = +1 frame'
                                 '\n Left Arrow = -1 frame'
                                 '\n Ctrl + s = Save annotations file'
                                 '\n Ctrl + a = +1 frame and keep choices'
                                 '\n Ctrl + l = Last frame'
                                 '\n Ctrl + o = First frame')
        self.key_presses_lbl.grid(sticky=S)
        self.__read_frm(frm_number=0)
        self.main_window.mainloop()

    def __bind_shortcut_keys(self):
        self.main_window.bind('<Control-s>', lambda x: self.__save_results())
        self.main_window.bind('<Control-a>', lambda x: self.__advance_frame(new_frm_number=int(self.current_frm_n.get() + 1), save_and_keep_checks=True))
        self.main_window.bind('<Right>', lambda x: self.__advance_frame(new_frm_number= int(self.current_frm_n.get() + 1)))
        self.main_window.bind('<Left>', lambda x: self.__advance_frame(new_frm_number= int(self.current_frm_n.get() - 1)))
        self.main_window.bind('<Control-l>', lambda x: self.__advance_frame(new_frm_number = self.max_frm_no))
        self.main_window.bind('<Control-o>', lambda x: self.__advance_frame(0))

    def __play_video(self):
        p = Popen('python {}'.format(self.play_video_script_path), stdin=PIPE, stdout=PIPE, shell=True)
        main_project_dir = os.path.dirname(self.config_path)
        p.stdin.write(bytes(self.video_path, 'utf-8'))
        p.stdin.close()
        temp_file = os.path.join(main_project_dir, 'subprocess.txt')
        with open(temp_file, "w") as text_file: text_file.write(str(p.pid))

    def __update_frame_from_video(self):
        f = open(os.path.join(os.path.dirname(self.config_path), 'labelling_info.txt'), 'r+')
        os.fsync(f.fileno())
        vid_frame_no = int(f.readline())
        self.__advance_frame(new_frm_number=vid_frame_no)
        f.close()

    def __read_frm(self, frm_number=None):
        self.cap.set(1, frm_number)
        _, self.current_frm_npy = self.cap.read()
        self.current_frm_npy = cv2.cvtColor(self.current_frm_npy, cv2.COLOR_RGB2BGR)
        self.current_frm_pil = Image.fromarray(self.current_frm_npy)
        self.current_frm_pil.thumbnail(self.max_frm_size, Image.ANTIALIAS)
        self.current_frm_pil = ImageTk.PhotoImage(master=self.main_window, image=self.current_frm_pil)
        self.video_frame = Label(self.main_window, image=self.current_frm_pil)
        self.video_frame.image = self.current_frm_pil
        self.video_frame.grid(row=0, column=0)

    def __advance_frame(self, new_frm_number: int=None, save_and_keep_checks=False):
        if new_frm_number > self.max_frm_no:
            print("FRAME {} CANNOT BE SHOWN - YOU ARE VIEWING THE FINAL FRAME OF THE VIDEO (FRAME NUMBER {})".format(str(new_frm_number), str(self.max_frm_no)))
            self.current_frm_n = IntVar(value=self.max_frm_no)
            self.change_frm_box.delete(0, END)
            self.change_frm_box.insert(0, self.current_frm_n.get())
        elif new_frm_number < 0:
            print("FRAME {} CANNOT BE SHOWN - YOU ARE VIEWING THE FIRST FRAME OF THE VIDEO (FRAME NUMBER {})".format(str(new_frm_number), str(self.max_frm_no)))
            self.current_frm_n = IntVar(value=0)
            self.change_frm_box.delete(0, END)
            self.change_frm_box.insert(0, self.current_frm_n.get())
        else:
            self.__create_print_statements()
            self.current_frm_n = IntVar(value=new_frm_number)
            self.change_frm_box.delete(0, END)
            self.change_frm_box.insert(0, self.current_frm_n.get())
            if not save_and_keep_checks:
                for target in self.target_lst:
                    self.checkboxes[target]['var'].set(self.data_df_targets[target].loc[int(self.current_frm_n.get())])
            else:
                for target in self.target_lst:
                    self.checkboxes[target]['var'].set(self.data_df_targets[target].loc[int(self.current_frm_n.get() -1)])
                    self.save_behavior_in_frm(target=target)
            self.__read_frm(frm_number=int(self.current_frm_n.get()))


    def __save_behavior_in_range(self, start_frm=None, end_frm=None):
        if not self.range_on.get():
            print('SAVE RANGE ERROR: TO SAVE RANGE OF FRAMES, TICK THE `Frame range` checkbox before clicking `Save Range`')
            raise ValueError('SAVE RANGE ERROR: TO SAVE RANGE OF FRAMES, TICK THE `Frame range` checkbox before clicking `Save Range`')
        else:
            check_int('START FRAME', int(start_frm), max_value=self.max_frm_no, min_value=0)
            check_int('END FRAME', int(end_frm), max_value=self.max_frm_no, min_value=0)
            for frm_no in range(int(start_frm), int(end_frm) + 1):
                for target in self.target_lst:
                    self.data_df_targets[target].loc[frm_no] = self.checkboxes[target]['var'][target].get()
            self.__read_frm(frm_number=int(end_frm))
            self.change_frm_box.delete(0, END)
            self.change_frm_box.insert(0, end_frm)
        self.__create_print_statements(frame_range=True, start_frame=start_frm, end_frame=end_frm)

    def save_behavior_in_frm(self, frame_number=None, target=None):
        self.data_df_targets[target].loc[int(self.current_frm_n.get())] = self.checkboxes[target]['var'].get()

    def __save_results(self):
        self.save_df = read_df(self.features_extracted_file_path, self.file_type)
        self.save_df = pd.concat([self.save_df, self.data_df_targets], axis=1)
        try:
            save_df(self.save_df, self.file_type, self.targets_inserted_file_path)
        except Exception as e:
            print(e, 'SIMBA ERROR: File for video {} could not be saved.')
            raise FileExistsError
        print('Annotation file for video {} saved within the project_folder/csv/targets_inserted directory.'.format(self.video_name))
        if not self.config.has_section('Last saved frames'):
            self.config.add_section('Last saved frames')
        self.config.set('Last saved frames', str(self.video_name), str(self.current_frm_n.get()))
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def __create_print_statements(self, frame_range: bool=None, start_frame: int=None, end_frame: int=None):
        print('USER FRAME SELECTION(S):')
        if not frame_range:
            for target in self.target_lst:
                target_present_choice = self.checkboxes[target]['var'].get()
                if (target_present_choice == 0):
                    print('{} ABSENT IN FRAME {}'.format(target, self.current_frm_n.get()))
                if (target_present_choice == 1):
                    print('{} PRESENT IN FRAME {}'.format(target, self.current_frm_n.get()))

        if frame_range:
            for target in self.target_lst:
                target_present_choice = self.checkboxes[target]['var'].get()
                if (target_present_choice == 1):
                    print('{} PRESENT IN FRAMES {} to {}'.format(target, str(start_frame), str(end_frame)))
                elif (target_present_choice == 0):
                    print('{} ABSENT IN FRAMES {} to {}'.format(target, str(start_frame), str(end_frame)))

def select_labelling_video(config_path: str=None,
                           threshold_dict=None,
                           setting: str=None,
                           continuing: bool=None,
                           video_file_path=None):
    if setting is not 'pseudo':
        video_file_path = filedialog.askopenfilename()
    else:
        threshold_dict_values = {}
        for k, v in threshold_dict.items():
             check_float(name=k, value=float(v.entry_get), min_value=0.0, max_value=1.0)
             threshold_dict_values[k] = float(v.entry_get)
        threshold_dict = threshold_dict_values

    check_file_exist_and_readable(video_file_path)
    video_meta = get_video_meta_data(video_file_path)
    _, video_name, _ = get_fn_ext(video_file_path)
    print(threshold_dict)


    print('ANNOTATING VIDEO {}: '.format(video_name))
    print('VIDEO INFO')
    print(video_meta)
    _ = LabellingInterface(config_path=config_path,
                          file_path=video_file_path,
                          threshold_dict=threshold_dict,
                          setting=setting,
                          continuing=continuing)

# test = select_labelling_video(config_path='/Users/simon/Desktop/troubleshooting/train_model_project/project_folder/project_config.ini',
#                           threshold_dict={'Attack': 0.4},
#                           setting='pseudo',
#                           continuing=False)
