#!/usr/bin/env python3

import argparse
import os
import sys
import cv2

from openvino.inference_engine import IECore

from detector import Detector
from estimator import HumanPoseEstimator

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
import monitors
from images_capture import open_images_capture


def build_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m_od", "--model_od", type=str, required=True,
                        help="path to model of object detector in xml format")

    parser.add_argument("-m_hpe", "--model_hpe", type=str, required=True,
                        help="path to model of human pose estimator in xml format")
    parser.add_argument("-i", "--input",
                        help="Required. An input to process. The input must be a single image, "
                             "a folder of images or anything that cv2.VideoCapture can process.")
    parser.add_argument("-loop", "--loop", default=False, action="store_true",
                        help="Optional. Enable reading the input in a loop.")
    parser.add_argument("-d", "--device", type=str, default='CPU', required=False,
                        help="Specify the target to infer on CPU or GPU")
    parser.add_argument("--person_label", type=int, required=False, default=15, help="Label of class person for detector")
    parser.add_argument("--no_show", help='Optional. Do not display output.', action='store_true')
    parser.add_argument("-u", "--utilization_monitors", default="", type=str,
                        help="Optional. List of monitors to show initially.")
    return parser


def run_demo(args):
    ie = IECore()
    detector_person = Detector(ie, path_to_model_xml=args.model_od,
                              device=args.device,
                              label_class=args.person_label)

    single_human_pose_estimator = HumanPoseEstimator(ie, path_to_model_xml=args.model_hpe,
                                                  device=args.device)
    cap = open_images_capture(args.input, args.loop)
    frame = cap.read()
    if frame is None:
        raise RuntimeError("Can't read an image from the input")
    delay = int(cap.get_type() in ('VIDEO', 'CAMERA'))

    presenter = monitors.Presenter(args.utilization_monitors, 25)
    while frame is not None:
        bboxes = detector_person.detect(frame)
        human_poses = [single_human_pose_estimator.estimate(frame, bbox) for bbox in bboxes]

        presenter.drawGraphs(frame)

        colors = [(0, 0, 255),
                  (255, 0, 0), (0, 255, 0), (255, 0, 0), (0, 255, 0),
                  (255, 0, 0), (0, 255, 0), (255, 0, 0), (0, 255, 0),
                  (255, 0, 0), (0, 255, 0), (255, 0, 0), (0, 255, 0),
                  (255, 0, 0), (0, 255, 0), (255, 0, 0), (0, 255, 0)]

        for pose, bbox in zip(human_poses, bboxes):
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), (255, 0, 0), 2)
            for id_kpt, kpt in enumerate(pose):
                cv2.circle(frame, (int(kpt[0]), int(kpt[1])), 3, colors[id_kpt], -1)

        cv2.putText(frame, 'summary: {:.1f} FPS (estimation: {:.1f} FPS / detection: {:.1f} FPS)'.format(
            float(1 / (detector_person.infer_time + single_human_pose_estimator.infer_time * len(human_poses))),
            float(1 / single_human_pose_estimator.infer_time),
            float(1 / detector_person.infer_time)), (5, 15), cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 0, 200))
        if not args.no_show:
            cv2.imshow('Human Pose Estimation Demo', frame)
            key = cv2.waitKey(delay)
            if key == 27:
                break
            presenter.handleKey(key)
        frame = cap.read()
    print(presenter.reportMeans())

if __name__ == "__main__":
    args = build_argparser().parse_args()
    run_demo(args)
