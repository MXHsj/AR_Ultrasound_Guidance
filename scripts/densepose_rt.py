import numpy as np
from cv2 import aruco
import matplotlib.pyplot as plt
import math
import time
from cv2 import cv2


def multidim_intersect(arr1, arr2):
    arr1_view = arr1.view([('', arr1.dtype)]*arr1.shape[1])
    arr2_view = arr2.view([('', arr2.dtype)]*arr2.shape[1])
    intersected = np.intersect1d(arr1_view, arr2_view)

    return intersected.view(arr1.dtype).reshape(-1, arr1.shape[1])


def getBodyPart(IUV, part_id):
    IUV_chest = np.zeros((IUV.shape[0], IUV.shape[1], IUV.shape[2]))
    torso_idx = np.where(IUV[:, :, 0] == part_id)
    IUV_chest[torso_idx] = IUV[torso_idx]

    return IUV_chest


def divide2region(frame, IUV_chest, target_u, target_v, pos):

    Radius = 15    # radius to mark circular region
    shape_color = (200, 200, 200)
    text_color = (1, 100, 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    error_rec = list()

    for reg in range(1, len(target_u)+1):
        u2xy_pair = np.where(
            IUV_chest[:, :, 1] == target_u[reg-1])    # xy paris in u
        v2xy_pair = np.where(
            IUV_chest[:, :, 2] == target_v[reg-1])    # xy pairs in v

        rcand = list()
        ccand = list()

        u_x = u2xy_pair[1]
        u_y = u2xy_pair[0]
        v_x = v2xy_pair[1]
        v_y = v2xy_pair[0]

        # need further optimization
        x_intersects = [x for x in u_x if x in v_x]
        y_intersects = [y for y in u_y if y in v_y]

        rcand = y_intersects
        ccand = x_intersects

        # u2xy_new = np.array(u2xy_pair).transpose()
        # v2xy_new = np.array(v2xy_pair).transpose()
        # try:
        #     xy_intersects = multidim_intersect(v2xy_new, u2xy_new)
        #     print(xy_intersects)
        #     # rcand.append(xy_intersects[1][0])
        #     # ccand.append(xy_intersects[0][0])
        #     # print(ccand)
        # except Exception as e:
        #     print('error: '+str(e))

        # for uind in range(len(u2xy_pair[0])):
        #     for vind in range(len(v2xy_pair[0])):
        #         x_u = u2xy_pair[1][uind]
        #         y_u = u2xy_pair[0][uind]
        #         x_v = v2xy_pair[1][vind]
        #         y_v = v2xy_pair[0][vind]
        #         if x_u == x_v and y_u == y_v:       # if xy pair intersects
        #             rcand.append(y_u)
        #             ccand.append(x_u)

        # print("\n rcand:", rcand, "\n ccand:", ccand)

        if len(rcand) > 0 and len(ccand) > 0:
            cen_col = int(np.mean(ccand))  # averaging col indicies
            cen_row = int(np.mean(rcand))  # averaging row indicies
            coord = (cen_col, cen_row)
            frame = cv2.circle(frame, coord, Radius, shape_color, -1)
            cv2.putText(frame, str(reg), coord, font,
                        0.5, text_color, thickness=2)
            if pos[reg-1, 0] != -1:
                dxsq = (cen_row - pos[reg-1, 1])*(cen_row - pos[reg-1, 1])
                dysq = (cen_col - pos[reg-1, 0])*(cen_col - pos[reg-1, 0])
                error = np.sqrt(dxsq+dysq)
            else:
                error = -1
        else:
            error = -1

        error_rec.append(error)
        print("region{} error: ".format(reg)+str(error))

    return frame, error_rec


def detectMarker(frame):
    # marker detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
    parameters = aruco.DetectorParameters_create()
    corners, ids, _ = aruco.detectMarkers(
        gray, aruco_dict, parameters=parameters)
    marker_frame = aruco.drawDetectedMarkers(frame.copy(), corners, ids)

    return marker_frame, corners, ids


def trackMarker(corners, ids):
    num_markers = 4
    pos = np.zeros((num_markers, 2))
    for i in range(1, num_markers+1):
        try:
            marker = corners[np.where(ids == i)[0][0]][0]
            pos[i-1, :] = [marker[:, 0].mean(), marker[:, 1].mean()]
        except:
            pos[i-1, :] = [-1, -1]      # if marker is not detected
        # print("id{} center:".format(i), pos[i-1, 0], pos[i-1, 1])

    return pos


def initVideoStream():
    cap = cv2.VideoCapture(2)
    focus = 0               # min: 0, max: 255, increment:5
    cap.set(28, focus)      # manually set focus
    return cap


def getVideoStream(cap):
    # patch_size = 480
    _, frame = cap.read()
    # frame = cv2.resize(frame, (patch_size, patch_size))
    frame = frame[:, 80:560]
    return frame


def main():
    part_id = 2     # 1 -> back; 2 -> torso

    if part_id == 2:
        target_u = [60, 100, 60, 100]
        target_v = [152, 167, 85, 82]
    elif part_id == 1:
        target_u = [80, 80]
        target_v = [167, 82]

    cap = initVideoStream()
    curr_time = 0
    time = list()
    reg1_error = list()
    reg2_error = list()
    reg3_error = list()
    reg4_error = list()
    fig = plt.figure()
    # plt.ion()

    while(True):
        frame = getVideoStream(cap)
        # cv2.imshow('frame', frame)

        save_path = '/home/xihan/Myworkspace/lung_ultrasound/image_buffer/incoming.png'
        cv2.imwrite(save_path, frame)

        frame, corners, ids = detectMarker(frame)
        pos = trackMarker(corners, ids)

        try:
            inferred = cv2.imread(
                '/home/xihan/Myworkspace/lung_ultrasound/infer_out/incoming_IUV.png')
        except Exception as e:
            print('error: '+str(e))

        if inferred is not None:
            IUV_chest = getBodyPart(inferred, part_id)
            frame, errors = divide2region(
                frame, IUV_chest, target_u, target_v, pos)
            reg1_error.append(errors[0])
            reg2_error.append(errors[1])
            reg3_error.append(errors[2])
            reg4_error.append(errors[3])
        else:
            reg1_error.append(-1)
            reg2_error.append(-1)
            reg3_error.append(-1)
            reg4_error.append(-1)

        cv2.imshow('overlay', frame)
        time.append(curr_time)

        if cv2.waitKey(1) & 0xFF == ord('q'):   # quit
            print('exiting ...')
            break

        curr_time = curr_time + 1

    # plt.cla()
    plt.plot(time, reg1_error, label='region 1 error')
    plt.plot(time, reg2_error, label='region 2 error')
    plt.plot(time, reg3_error, label='region 3 error')
    plt.plot(time, reg4_error, label='region 4 error')
    plt.ylabel('error in pixels')
    plt.xlabel('time stamp')
    plt.legend(loc="upper left")
    plt.show()
    # plt.pause(.00001)
    # plt.ioff()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
