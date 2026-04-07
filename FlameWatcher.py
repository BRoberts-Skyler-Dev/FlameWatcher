# -*- coding: utf-8 -*-
"""
Created on Fri Mar  27 11:49:50 2026

@author: Skyler (Benjamin) Roberts
"""

import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from harvesters.core import Harvester
from collections import deque
import threading
import queue
import subprocess
import os
from colorama import init, Fore, Back, Style





#Init functions
start_time = time.time()
timestr = time.strftime("%Y%m%d-%H%M%S")
response_array = []
times = []
position = []
lum = []
fps=100
fps_log = []
fps_deque_max = []
fps_deque_min = []
fps_std_max = []
fps_std_min = []
fps_avg=[]
fps_deque = deque(maxlen=20)
position_deque = deque(maxlen=60)
prev_position_deque = deque(maxlen=60)
frame_durations = []
alpha = 0.1 #smoothing factor, adjust between 0 and 0.5
timestart = time.time()
prev_time = timestart
prev_centre_y=None
prev_leading_y=None
crop_factor = 2 # higher values are a larger crop, e,g, 2 splits into half, 3 takes a middle third, etc; dont go below 1.
threshold=0.08/crop_factor #auto adjusts the base threshold to the crop size. see README.
imageswitch="display"

#Set this to desired save folder

save_path =


#Set this to wherever your CTI file is for Harvesters

CTI_FILE = 



#Path functions
display_raw_path = save_path + "display_raw.bin"
thresh_raw_path  = save_path + "thresh_raw.bin"
display_mp4_path = save_path + timestr + "CentroidVideo.mp4"
thresh_mp4_path  = save_path + timestr + "ThreshCentroidVideo.mp4"


#Harvesters init

harv = Harvester()
harv.add_file(CTI_FILE)
harv.update()
print(harv.device_info_list)
ia = harv.create(0)

ia.start()


# Grab one frame first to get the dimensions
with ia.fetch() as buffer:
    component = buffer.payload.components[0]
    frame_width = component.width
    frame_height = component.height


#Writer queuer and ffmpeg functions
write_queue = queue.Queue(maxsize=50)

def writer_thread(q):
    display_out = open(display_raw_path, "wb")
    thresh_out = open(thresh_raw_path, "wb")
    while True:
        item = q.get()
        if item is None:
            break
        display_frame, CentroidBGR = item
        display_out.write(display_frame.tobytes())
        thresh_out.write(CentroidBGR.tobytes())
    display_out.close()
    thresh_out.close()
    
    
#This handles the ffmpeg encoding using timestamped images. Unlike openCV's write, it can keep accurate time with dropped frames
def encode_with_timestamps(raw_path, output_path, durations, width, height):
    frames_dir = raw_path.replace(".bin", "_frames")
    os.makedirs(frames_dir, exist_ok=True)
    name = os.path.basename(raw_path)
    try:
        # Split bin into individual frame files
        frame_size = width * height * 3
        bin_size = os.path.getsize(raw_path)
        actual_frames = bin_size // frame_size
        print(f"{name} - Frames in bin: {actual_frames}")
        with open(raw_path, "rb") as f:
            for i, d in enumerate(durations):
                raw_frame = f.read(frame_size)
                img = np.frombuffer(raw_frame, dtype=np.uint8).reshape(height, width, 3)
                cv2.imwrite(os.path.join(frames_dir, f"frame_{i:06d}.png"), img)
        print(Fore.LIGHTGREEN_EX + f"{name} - Image write complete")
    
        # Write concat file
        concat_path = raw_path.replace(".bin", "_concat.txt")
        with open(concat_path, "w") as f:
            for i, d in enumerate(durations):
                frame_path = os.path.join(frames_dir, f"frame_{i:06d}.png").replace("\\", "/")
                f.write(f"file '{frame_path}'\n")
                f.write(f"duration {d:.6f}\n")
                
        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_path.replace("\\", "/"),
            "-vcodec", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            output_path
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr)
           #raise RuntimeError("FFmpeg failed on encode step")
        print(f"{name} - Encoding complete")
    finally:
        # always clean up regardless of success or failure
        if os.path.exists(frames_dir):
            for f in os.listdir(frames_dir):
                os.remove(os.path.join(frames_dir, f))
            os.rmdir(frames_dir)
        if os.path.exists(concat_path):
            os.remove(concat_path)
        if os.path.exists(raw_path):
            os.remove(raw_path)
        print(f"{name} - Cleanup complete")

wt = threading.Thread(target=writer_thread, args=(write_queue,), daemon=True)
wt.start()
for _ in range(10):
    cv2.waitKey(1)



#Thresholder - this is the part detecting and tracking the flame


prev_time = time.time()
try:
    while True:
        with ia.fetch() as buffer:
            component = buffer.payload.components[0]

            img = component.data.reshape(
                component.height,
                component.width,
                int(component.num_components_per_pixel)
            )

            frame = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BayerRG2GRAY)
            
            #Cut down frame
            h, w = frame.shape

            x_start = w // (crop_factor * 2)
            x_end = w-x_start
            y_start = 0
            y_end = h-y_start
            
            middle = frame[y_start:y_end, x_start:x_end]

            
            #Quit using q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            
            #Main Thresholder
            
            ret,thresh = cv2.threshold(middle,50,255,cv2.THRESH_BINARY)
            row_sum = np.sum(middle,axis=1)/1000000
            top_idx = np.argmax(row_sum>threshold)
            bottom_idx = len(row_sum)-np.argmax(row_sum[::-1]>threshold) -1
            top_y = top_idx
            bottom_y = bottom_idx
            centre_y = (bottom_y+top_y)/2
            position_deque.append(centre_y)
            if len(position_deque) == 20:
                prev_position_deque.append(position_deque[0])
            interval = time.time()-prev_time
            
            
            #Assuming the flame burns downwards, tracks the bottom of the flame.
            leading_y = bottom_y
            
            
            #Ensures last position is held if flame goes out of frame, as well as smoothing
            if max(row_sum)>threshold:
                if prev_leading_y is not None:
                    leading_y = int(alpha*prev_leading_y + (1-alpha)*leading_y)
            if max(row_sum)<threshold:
                if prev_leading_y is not None:
                    leading_y = prev_leading_y
            
            prev_leading_y = leading_y
            
            
            #Response code and log, useful for panning a camera.
            
            response_scalar = abs(5*(leading_y-(frame_height*0.5))/(frame_height))-7.5*(0.1)
            if response_scalar < 0:
                response_scalar = 0
            if response_scalar > 1:
                response_scalar = 1
            if leading_y < frame_height*0.5:
                response_scalar = -response_scalar
            response_array.append(response_scalar)
            
            #Video processor
            middle_h, middle_w = middle.shape
            threshcentreX = middle_w // 2
            centreX = w // 2
            
            CentroidBGR = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            cv2.circle(CentroidBGR, (threshcentreX,bottom_y), 5, (0,155,255),2)
            
            display_frame=cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            cv2.line(display_frame, (x_start, 0), (x_start, h), (0, 255, 255), 1)
            cv2.line(display_frame, (x_end, 0), (x_end, h), (0, 255, 255), 1)
            cv2.circle(display_frame, (centreX,leading_y), 5, (0,155,255),2)
            
            
            
            #Trackers

            fps_actual = 1.0 / interval if interval > 0 else 0
            fps_log.append(fps_actual)
            fps_deque.append(fps_actual)
            fps_avg.append(np.mean(fps_deque))
            fps_deque_max.append(np.max(fps_deque))
            fps_deque_min.append(min(fps_deque))
            fps_std_max.append(np.mean(fps_deque)+np.std(fps_deque))
            fps_std_min.append(np.mean(fps_deque)-np.std(fps_deque))
            times.append(prev_time-start_time)
            position.append(frame_height-leading_y) # more intuitive on graph, despite openCV counting the other way
            Luminosity = np.sum(row_sum)
            lum.append(Luminosity)

            # Viewport
            divider = np.zeros((frame_height, 4, 3), dtype=np.uint8)
            combined = np.hstack((display_frame, divider, CentroidBGR))
            now = time.time()
            interval = now - prev_time
            prev_time = now
            write_queue.put((display_frame.copy(), CentroidBGR.copy()))
            frame_durations.append(interval)
            cv2.imshow("Allied Vision Feed", combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break



# Plots- it's helpful to visually understand behaviour

    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(12, 6))
    
    headroom = 1.1
    ylim_ax1 = headroom*max(response_array)
    ylim_ax2 = headroom*max(position)
    ylim_ax3 = headroom*max(lum)
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    
    # Measurement / control axes
    
    # Primary axis - response
    ax1.plot(times,response_array, color='mediumvioletred')
    ax1.set_ylabel('Response vector', color ='mediumvioletred', fontname='Times New Roman', fontweight='bold', fontsize="12")
    ax1.tick_params(axis='y', labelcolor='mediumvioletred')
    ax1.set_ylim([-1.1,1.1])
    ax1.set_xlim([0,sum(frame_durations)])    
    # Create secondary y-axis for position log
    ax2 = ax1.twinx()
    ax2.plot(times, position, color='darkred')
    ax2.set_ylabel('Position', color='darkred', fontname='Times New Roman', fontweight='bold', fontsize="12")
    ax2.tick_params(axis='y', labelcolor='darkred')
    #ax2.axhline(1080/2, color='gray', linewidth=0.5)
    ax2.axhline(0.85*frame_height, color='gainsboro', linewidth=1)
    ax2.axhline(0.35*frame_height, color='gray', linewidth=0.5)
    ax2.axhline(0.65*frame_height, color='gray', linewidth=0.5)
    ax2.axhline(0.15*frame_height, color='gainsboro', linewidth=1)
    ax2.set_ylim([0,frame_height])
    
    #Diagnostics / performance axes
    
    #Tertiary axis
    ax3.plot(times, fps_avg, color='orangered', linewidth=0.5)
    ax3.fill_between(times, fps_deque_min, fps_deque_max, color='orangered', alpha=0.1, label='Min-Max FPS Range')
    ax3.fill_between(times, fps_std_min, fps_std_max, color='orangered', alpha=0.1, label='Min-Max FPS Range')
    ax3.set_ylabel('FPS 20-frame mean', color='orangered', fontname='Times New Roman', fontweight='bold', fontsize="12")
    ax3.tick_params(axis='y', labelcolor='orangered')
    ax1.set_xlim([0,sum(frame_durations)]) 
    
    #Quaternary axis
    # ax4 = ax3.twinx()
    # ax4.plot(times,lum, color='lightblue')
    # ax4.set_ylabel('Luminosity', color ='lightblue', fontname='Times New Roman', fontweight='bold', fontsize="16")
    # ax4.tick_params(axis='y', labelcolor='lightblue')
    # ax4.set_ylim([0,ylim_ax3])
    # ax4.spines['right'].set_position(('outward',60))
    
finally:
    fintime = (time.time() - start_time)
    print(fintime) # should be similar to Video Length
    write_queue.put(None) # poison pill on queue
    wt.join()
    encode_with_timestamps(display_raw_path, display_mp4_path, frame_durations, frame_width, frame_height)
    encode_with_timestamps(thresh_raw_path,  thresh_mp4_path,  frame_durations, frame_width // crop_factor, frame_height)
    
    cv2.destroyAllWindows()
    ia.stop()
    ia.destroy()
    harv.reset()
    print("Script complete")
    print(f"Video length: {sum(frame_durations):.2f}s")
    print(f"Max framerate: {1/min(frame_durations):.0f}fps")
    print(f"Min framrate: {1/max(frame_durations):.0f}fps")
    