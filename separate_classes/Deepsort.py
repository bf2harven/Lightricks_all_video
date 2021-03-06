import numpy as np
import cv2
import matplotlib.pyplot as plt
import os
import pickle as pkl
import multiprocessing
import pandas as pd
import torch


class Tracker:
    def __init__(self, df_path: str) -> None:
        self.df = pd.read_csv(df_path, header=None, sep=' ')
        self.df.drop([6, 7, 8, 9, 10], axis=1, inplace=True)
        self.df.columns = ['frame_number',
                           'person_id', 'x0', 'y0', 'width', 'height']

    def impute_bboxes(self, df, person_id=1, n_frames=300, smooth_window=10):
        """
        Takes a dataframe of bounding boxes, and for each person, it imputes the missing bounding
        boxes by taking a rolling average of the bounding boxes
        
        :param df: the dataframe containing the bounding boxes
        :param person_id: the person you want to impute, defaults to 1 (optional)
        :param n_frames: the number of frames in the video, defaults to 300 (optional)
        :param smooth_window: the number of frames to smooth over, defaults to 10 (optional)
        :return: A dataframe with the imputed bounding boxes.
        """
        df0 = pd.DataFrame({'frame_number': range(n_frames)})
        df1 = df[df.person_id == person_id]
        df1.loc[:, 'rolling_x0'] = df1.x0.rolling(
            smooth_window, min_periods=1).mean().astype(int)
        df1.loc[:, 'rolling_y0'] = df1.y0.rolling(
            smooth_window, min_periods=1).mean().astype(int)
        df1.loc[:, 'rolling_width'] = df1.width.rolling(
            smooth_window, min_periods=1).mean().astype(int)
        df1.loc[:, 'rolling_height'] = df1.height.rolling(
            smooth_window, min_periods=1).mean().astype(int)
        df0 = df0.merge(df1, on='frame_number', how='outer')
        df0['is_imputed'] = df0.x0.isna()
        df0.interpolate(inplace=True, limit_direction='both')
        df0.dropna(inplace=True)
        return df0.astype(int)

    def create_person_subclip(self, video, df_smooth, aspect_ratio_max=1):
        """
        It takes a video and a dataframe of bounding boxes and returns a list of frames with the person
        centered in the frame.
        
        :param video: the video file
        :param df_smooth: a dataframe with the following columns:
        :param aspect_ratio_max: The maximum aspect ratio of the person's bounding box, defaults to 1
        (optional)
        :return: A list of frames
        """
        frames_out = []
        width = df_smooth.rolling_width.median().astype(int)
        height = df_smooth.rolling_height.median().astype(int)
        if height > width:
            width = max(width, int(aspect_ratio_max*height))
        else:
            height = max(height, int(aspect_ratio_max*width))

        for frame_number, X,	Y,	_,	_ in df_smooth.loc[::1, ['frame_number', 'rolling_x0',	'rolling_y0', 'rolling_width', 'rolling_height']].values:
            if X - width//2 < 0:
                x0 = 0
            else:
                x0 = X - int(width//2)
            if Y - height//2 < 0:
                y0 = 0
            else:
                y0 = Y - int(height//2)
            x1 = X + width
            y1 = Y + height
            frame = video[frame_number, y0:y1, x0:x1, :]
            frame = cv2.resize((frame/255.).astype('float32'), (172, 172))
            frames_out.append(frame[:, :, ::-1])

        return frames_out
