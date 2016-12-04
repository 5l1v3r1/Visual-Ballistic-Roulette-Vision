import os
from collections import deque

import cv2
import dill
import numpy as np

from utils import FrameIterator, CROPPED_GRADIENTS_DIR, frames_to_seconds


def bucket_analysis(buckets):
    keep_buckets = []
    print('{} buckets to analyze'.format(len(buckets)))
    for bucket in buckets:
        the_one_the_most_at_the_right_idx = np.argmax([t[0][1] for t in bucket])
        keep_buckets.append(bucket[the_one_the_most_at_the_right_idx])
    return keep_buckets


def bucket_frames(results):
    # complexity MUST NOT BE QUADRATIC.
    # ball must at least be there for two consecutive frames.
    valid_frames = []
    last_known_result = (None, -1)
    bucket = []
    for result in results:
        cur_frame = result[1]
        if cur_frame <= last_known_result[1] + 3:
            if len(bucket) == 0:
                # push the former element.
                bucket.append(last_known_result)
            bucket.append(result)  # start filling the bucket.
        else:
            if len(bucket) > 0:
                valid_frames.append(bucket.copy())  # push the bucket.
            bucket = []  # reset the bucket.
        last_known_result = result
    return valid_frames


def analyze_video():
    # B max 177 min 147
    # G max 195 min 150
    # R max 227 min 172

    # B G R
    white_lower = (10, 10, 10)
    white_upper = (255, 255, 255)
    pts = deque(maxlen=64)
    results = []

    frame_iterator = FrameIterator(CROPPED_GRADIENTS_DIR)
    for i, frame in enumerate(frame_iterator.read_frames()):

        mask = cv2.inRange(frame, white_lower, white_upper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        cv2.imshow("Mask", mask)

        # find contours in the mask and initialize the current (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None

        # only proceed if at least one contour was found
        if len(cnts) > 0:
            # find the largest contour in the mask, then use
            # it to compute the minimum enclosing circle and
            # centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            # only proceed if the radius meets a minimum size
            if radius > 1:
                # draw the circle and centroid on the frame,
                # then update the list of tracked points
                cv2.circle(frame, (int(x), int(y)), int(radius), (255, 255, 0), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)
                results.append((center, i))
                print(center, i)

        # update the points queue
        pts.appendleft(center)
        # loop over the set of tracked points
        for i in range(1, len(pts)):
            # if either of the tracked points are None, ignore
            # them
            if pts[i - 1] is None or pts[i] is None:
                continue

            # otherwise, compute the thickness of the line and draw the connecting lines
            thickness = int(np.sqrt(64 / float(i + 1)) * 2.5)
            cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

        # show the frame to our screen
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the 'q' key is pressed, stop the loop
        if key == ord("q"):
            break

    cv2.destroyAllWindows()
    return results


def start():
    if os.path.isfile('res.pkl'):
        r = dill.load(open('res.pkl', 'rb'))
    else:
        r = analyze_video()
        dill.dump(r, open('res.pkl', 'wb'))

    from pprint import pprint

    pprint(r)
    print('\n ---  \n')
    b = bucket_frames(r)
    a = bucket_analysis(b)
    pprint(b)
    pprint(a)
    pprint(len(a))
    frames_seconds = frames_to_seconds(np.array([c[1] for c in a]))
    print(frames_seconds)
    print(np.diff(frames_seconds))
    # NOT CORRECT NOW. HAVE TO SHIFT.


if __name__ == '__main__':
    start()