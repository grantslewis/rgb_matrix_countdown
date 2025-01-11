# Heavily Modified from code provided by John Park for Adafruit Industries (2020)

import time
import os
import board
import displayio
from digitalio import DigitalInOut, Pull
from adafruit_matrixportal.matrix import Matrix
from adafruit_debouncer import Debouncer
from adafruit_display_text import label
from terminalio import FONT
import rtc as RTC
import asyncio
from values import MONTHS, MONTH_DAY_MAXES, COLORS

# SCREEN CAN FIT 10 lowercase m's!!!


# Set to True to disable time setting on boot
DISABLE_TIME_SET = False

rtc = RTC.RTC()
# The time that the countdown will start at (Can be set using the buttons on boot)
rtc.datetime = time.struct_time((2024, 12, 27, 12, 11, 0, 0, -1, -1))

# The time that the countdown will end at (Can be set using the buttons on boot)
time_finished = time.struct_time((2025, 7, 31, 17, 0, 0, 0, -1, -1))


# Defining the buttons
# Button 1 is used to increment and decrement the time
button_1 = DigitalInOut(board.GP21)
button_1.switch_to_input(pull=Pull.UP)
button_1 = Debouncer(button_1)

# Button 2 is used to switch between the different time values
button_2 = DigitalInOut(board.GP22)
button_2.switch_to_input(pull=Pull.UP)
button_2 = Debouncer(button_2)

# Setting up listeners for the buttons asynchronously
def button_listener(button, callback, long_press_callback):
    async def listener():
        while True:
            button.update()
            start_value = button.value
            if button.fell: # if button is being pressed
                is_long = True
                for _ in range(5): # If button is pressed for an extended period of time (note, rapidly pressing can be registered as a long press. You could potentially add more frequent checks to make this more accurate.)
                    button.update()
                    if button.value != start_value:
                        is_long = False
                        break
                    await asyncio.sleep(0.1)
                if is_long:
                    long_press_callback()
                    continue
                else:
                    callback()
            await asyncio.sleep(0.01)
            
    asyncio.create_task(listener())

# Defining the callback manager class. This allows functionality of the buttons to be changed dynamically
class callback_manager:
    def __init__(self, cb_name=''):
        self.callback_name = cb_name
        self.callback_function = self.default_callback()
        
    def default_callback(self):
        print(f'default callback {self.callback_name}')
        
    def reset(self):
        self.callback_function = self.default_callback()
        
    def __call__(self, *args, **kwds):
        self.callback_function(*args, **kwds)

# Instantiating the listeners and callback managers for the buttons
b_1_cb = callback_manager('button 1')
b_2_cb = callback_manager('button 2')
b_1_long_cb = callback_manager('button 1 long')
b_2_long_cb = callback_manager('button 2 long')
button_listener(button_1, b_1_cb, b_1_long_cb)
button_listener(button_2, b_2_cb, b_2_long_cb)

# May need to uncomment this but probably not
# async def main():
#     while True:
#         await asyncio.sleep(1)

print('Button listeners set up')

DEFAULT_FRAME_DURATION = 0.1  # 100ms
BMP_REPEAT_COUNT = 3 # Number of times to repeat showing a bmp image/gif
MATRIX_HEIGHT = 32 # Number of pixels tall the display is
MATRIX_WIDTH = 64 # Number of pixels wide the display is
COUNT_DUR_MULT = 2 # Number of times to iterate over the colors for the countdown phase
CLOCK_DUR = 20 # Number of seconds to display the clock phase for


# --- Display setup ---
matrix = Matrix(bit_depth=2)
sprite_group = displayio.Group()
matrix.display.show(sprite_group)


# -- Start of time setting code --
class date_time:
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None):
        
        time = rtc.datetime
        self.times = {
            'year': time.tm_year if year is None else year,
            'month': time.tm_mon if month is None else month,
            'day': time.tm_mday if day is None else day,
            'hour': time.tm_hour if hour is None else hour,
            'minute': time.tm_min if minute is None else minute
        }
        self.order = ['year', 'month', 'day', 'hour', 'minute']
        
        self.maxes = [2100, 12, 31, 23, 59] # Allow for number roll over of values from min to max or max to min # If this runs past the year 2100, congratulations! You've broken the code :)
        self.mins = [2024, 1, 1, 0, 0]
        self.index = 0
        self.b_2_unresolved = False
        
    def max_month_days(self):
        is_leap = (self.times['year'] % 4 == 0 and self.times['year'] % 100 != 0) or (self.times['year'] % 400 == 0)
        day_cnt = MONTH_DAY_MAXES[self.times['month']]
        
        if self.times['month'] == 2 and is_leap:
            day_cnt += 1
        return day_cnt
        
    def increment(self, index): # Increment the current value
        self.times[self.order[index]] += 1
        # if (self.times[self.order[index]] > self.maxes[index]) or (self.order[index] == 'day' and self.times[self.order[index]] > MONTH_DAY_MAXES[self.times['month']]):
        if (self.times[self.order[index]] > self.maxes[index]) or (self.order[index] == 'day' and self.times[self.order[index]] > self.max_month_days()):                
            self.times[self.order[index]] = self.mins[index]
        print('incremented:', self.order[index], self.times[self.order[index]])
    
    def decrement(self, index): # Decrement the current value
        self.times[self.order[index]] -= 1
        if (self.times[self.order[index]] < self.mins[index]):
            # max_val = MONTH_DAY_MAXES[self.times['month']] if self.order[index] == 'day' else self.maxes[index]
            max_val = self.max_month_days() if self.order[index] == 'day' else self.maxes[index]
            self.times[self.order[index]] = max_val
        print('decremented:', self.order[index], self.times[self.order[index]])
    
    def _inc_index(self): # Increment the index to the next value
        print('index incramented')
        self.index += 1
        self.b_2_unresolved = True
        
    def _dec_index(self): # Decrement the index to the previous value
        print('index decremented')
        self.index = max(self.index - 1, 0)
    
    async def set_values(self, text_modder=''): # Used to display the time being set and updating the callback functions
        # Set up the display
        print('start set_time')
        text_group = displayio.Group()
        matrix.display.show(text_group)
        text_area = label.Label(FONT, text="", color=0xFFFFFF, scale=1)
        text_area.x = 2  # Adjust for centering
        text_area.y = 6  # Adjust for centering
        text_group.append(text_area)

        # Set the callbacks
        b_1_cb.callback_function = lambda: self.increment(self.index)
        b_1_long_cb.callback_function = lambda: self.decrement(self.index)
        b_2_cb.callback_function = lambda: self._inc_index()
        b_2_long_cb.callback_function = lambda: self._dec_index()
        
        while True:
            while True:
                str_times = [f"{self.times[val]:02}" for val in self.order] + [text_modder] #, self.order[index]]
                FRMT = "{}-{}-{}\n{}:{}-{}" #\n{}"
                
                blinking = str_times[:]
                blinking[self.index] = "".join([" " for _ in range(len(str_times[self.index]))])
                
                text_str = FRMT.format(*str_times)
                blinking_str = FRMT.format(*blinking)
                
                text_area.text = text_str
                await asyncio.sleep(0.25)
                if self.b_2_unresolved:
                    self.b_2_unresolved = False
                    break
                                
                text_area.text = blinking_str
                await asyncio.sleep(0.25)
                if self.b_2_unresolved:
                    self.b_2_unresolved = False
                    break

            if self.index >= len(self.order) or self.index < 0:
                print('index >= len(self.order)')
                b_1_cb.reset()
                b_1_long_cb.reset()
                b_2_cb.reset()
                b_2_long_cb.reset()
                
                return
                
async def run():
    print('start')
    curr_time_set = date_time()
    await curr_time_set.set_values('Curr')

    dest_time_set = date_time(time_finished.tm_year, time_finished.tm_mon, time_finished.tm_mday, time_finished.tm_hour, time_finished.tm_min)
    await dest_time_set.set_values('Fin')
    print('end')
    return curr_time_set, dest_time_set

if not DISABLE_TIME_SET: # Set the current time and the time to count down to using the buttons
    curr_time_set, dest_time_set = asyncio.run(run())

    time_finished = time.struct_time((dest_time_set.times['year'], dest_time_set.times['month'], dest_time_set.times['day'], dest_time_set.times['hour'], dest_time_set.times['minute'], 0, 0, -1, -1))
    time_finished = time.mktime(time_finished)

    rtc.datetime = time.struct_time((curr_time_set.times['year'], curr_time_set.times['month'], curr_time_set.times['day'], curr_time_set.times['hour'], curr_time_set.times['minute'], 0, 0, -1, -1))
    time_set = time.mktime(rtc.datetime)
else:
    time_set = time.mktime(rtc.datetime)
    time_finished = time.mktime(time_finished)
# -- End of time setting code --


def time_to_finish():
    current_time = rtc.datetime
    remaining_time = time_finished - time.mktime(current_time)
    return remaining_time

class Timer:
    def __init__(self, remainder=None):
        if remainder is None:
            remainder = time_to_finish()
            
        self.remainder = remainder
        remaining_time = remainder
        
        self.seconds = remaining_time % 60
        remaining_time //= 60
        self.minutes = remaining_time % 60
        remaining_time //= 60
        self.hours = remaining_time % 24
        remaining_time //= 24
        self.days = remaining_time % 7
        remaining_time //= 7
        self.weeks = remaining_time
        
        self.times_up_cnt = 0

    
    def decrement(self):
        if self.is_finished():
            return 0, 0, 0, 0, 0
        
        self.seconds -= 1
        if self.seconds < 0:
            self.seconds = 59
            self.minutes -= 1
            
            if self.minutes < 0:
                self.minutes = 59
                self.hours -= 1
                
                if self.hours < 0:
                    self.hours = 23
                    self.days -= 1
                    
                    if self.days < 0:
                        self.days = 6
                        self.weeks -= 1
                        
                        if self.weeks < 0:
                            self.weeks = 0
                            self.days = 0
                            self.hours = 0
                            self.minutes = 0
                            self.seconds = 0
        return self.weeks, self.days, self.hours, self.minutes, self.seconds
    
    def formatted_decrement(self):
        # Returns formatted display text, scale, and offset tuple
        # Used for displaying the countdown differently based on the time remaining
        self.decrement()
        
        if self.weeks > 0: # This was included so that weeks could be displayed. The end user only wanted days, hours, minutes, and seconds displayed so weeks were converted to days for visualization
            # return f"{self.weeks}w {self.days}d\n{self.hours:02}:{self.minutes:02}:{self.seconds:02}", 1, (0, 0)
            days_full = (self.weeks * 7) + self.days
            return f"{days_full} days\n{self.hours:02}:{self.minutes:02}:{self.seconds:02}", 1, (0, 0)
            
        elif self.days > 0:
            return f"{self.days} days\n{self.hours:02}:{self.minutes:02}:{self.seconds:02}", 1, (0, 0)
        elif self.hours > 0:
            return f"{self.hours:2}:{self.minutes:02}:{self.seconds:02}", 1, (7, 9)
        elif self.minutes > 0:
            return f"{self.minutes:2}:{self.seconds}", 2, (1, 9)
        elif self.seconds > 0:
            return f"{self.seconds:2}", 4, (9, 10)
        else:
            self.times_up_cnt += 1
            return "Congratulations!", 1, (5, 9)

    def just_show_count(self): # If this is true, only the countdown will be shown (this occurs when there is less than an hour left)
        return (self.weeks == 0 and self.days == 0 and self.hours == 0)
    
    def is_finished(self):
        return (self.weeks == 0 and self.days == 0 and self.hours == 0 and self.minutes == 0 and self.seconds == 0)
    
    
def text_setup(font=FONT, text="", color=0xFFFFFF, offset=(2,6)):
    while sprite_group: # Clear any existing sprites
        sprite_group.pop()
        
    text_group = displayio.Group() # Build the new text group
    matrix.display.show(text_group)
    
    text_area = label.Label(font, text=text, color=color, scale=1) # Prepare the text area
    
    # Set the offset for the text area and add it to the group
    # Default offset is (2,6) was used since this worked best for the 64x32 display when font had a scale of 1
    text_area.x = offset[0]  # Adjust for centering
    text_area.y = offset[1]  # Adjust for centering
    text_group.append(text_area)
    return text_group, text_area

def count_down_phase(timer=None):
    # Display the countdown. Change the color every second
    if timer is None:
        timer = Timer()
    
    color_index = 0
    colors = COLORS
    base_offsets = (2,6)
    
    text_group, text_area = text_setup(text="", color=colors[color_index], offset=base_offsets)
    
    # Iterate over the colors and display the countdown (change color every second)
    # Iterate over every color COUNT_DUR_MULT times
    # If the timer is up, display the congratulations message for 10 iterations
    for _ in range(COUNT_DUR_MULT * len(colors)):
        text_area.color = colors[color_index]
        color_index = (color_index + 1) % len(colors)
        text_area.text, text_area.scale, offsets = timer.formatted_decrement()
        if timer.times_up_cnt > 10:
            break
        text_area.x = base_offsets[0] + offsets[0]
        text_area.y = base_offsets[1] + offsets[1]
        time.sleep(1)
    return
    
def clock_phase():
    # Show the date and time. Every second, alternate hiding and showing the ":" between the hours and minutes
    text_group, text_area = text_setup() 
    
    for _ in range(CLOCK_DUR // 2): # // 2 since each iteration is 2 seconds
        current_time = rtc.datetime
        date = "{} {}".format(MONTHS[current_time[1]], current_time[2])
        
        am_pm = "AM" if current_time[3] < 12 else "PM"
        hour = current_time[3] % 12
        if hour == 0:
            hour = 12
        full_time = "{:02}:{:02} {}".format(hour, current_time[4], am_pm)
        blink_time = "{:02} {:02} {}".format(hour, current_time[4], am_pm) 
        
        date = "{:^10}".format(date)
        full_time = "{:^10}".format(full_time)
        blink_time = "{:^10}".format(blink_time)
        
        time_str = date + '\n' + full_time
        blink = date + '\n' + blink_time
        
        text_area.text = time_str
        time.sleep(1)
        text_area.text = blink
        time.sleep(1)
    return

current_image = None
current_frame = 0
current_loop = 0
frame_count = 0
frame_duration = DEFAULT_FRAME_DURATION

sprite_group = None

def load_image(filename): #, x_offset=0):
    # Load an image as a sprite and display it
    # pylint: disable=global-statement
    global current_frame, current_loop, frame_count, frame_duration, sprite_group
    sprite_group = displayio.Group()
    matrix.display.show(sprite_group)

    print(filename)
    bitmap = displayio.OnDiskBitmap(open(filename, "rb"))
    sprite = displayio.TileGrid(
        bitmap,
        pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter()),
        tile_width=bitmap.width,
        tile_height=matrix.display.height,
    )
    
    x_offset = 0
    # Center images that are narrower than the display
    if bitmap.width < matrix.display.width:
        x_offset = (matrix.display.width - bitmap.width) // 2
        print('x_offset:', x_offset)
    sprite.x = x_offset
    sprite_group.append(sprite)
    print("len(sprite_group):", len(sprite_group)) #, len(sprite_group[0]))

    current_frame = 0
    current_loop = 0
    frame_count = int(bitmap.height / matrix.display.height)
    print('frame_count:', frame_count)
    frame_duration = DEFAULT_FRAME_DURATION
        
def advance_frame():
    # Advance to the next frame of the sprite (loop at the end)
    # pylint: disable=global-statement
    global current_frame, current_loop, sprite_group

    current_frame += 1
    if current_frame >= frame_count:
        current_frame = 0
        current_loop += 1
    sprite_group[0][0] = current_frame

def bmp_phase(filename, frame_duration=DEFAULT_FRAME_DURATION, is_still_image=False, bmp_repeat_count=BMP_REPEAT_COUNT):
    global current_frame, current_loop
    load_image(filename)
    
    for _ in range(bmp_repeat_count):
        while current_loop < BMP_REPEAT_COUNT:
            advance_frame()
            time.sleep(frame_duration)
            if is_still_image: # Don't try to loop
                continue
            while current_frame != 0:
                advance_frame()
                time.sleep(frame_duration)
    print('current_frame:', current_frame)
    current_loop = 0
    return 

def byu_phase():
    bmp_phase('./bmps/byu_sprite_sheet_bw_skinny.bmp')
    return

def us_flag_phase():
    bmp_phase('./bmps/us_flag.bmp', frame_duration=1, is_still_image=True)
    return

def firework_phase(bmp_repeat_count=BMP_REPEAT_COUNT):
    bmp_phase('./bmps/fireworks_skinny.bmp', bmp_repeat_count=bmp_repeat_count)
    return


timer = Timer()
while True:
    
    if not timer.just_show_count() or timer.is_finished():
        # If the time has a long time left, or if the timer is finished, display this sequence
        byu_phase()
        us_flag_phase()
        firework_phase()
        byu_phase()
        clock_phase()
        byu_phase()
        
    if not timer.is_finished():
        # Show the countdown if the timer is not finished
        count_down_phase(timer)
        
    if timer.is_finished():
        # Timer is finished, so display extra fireworks
        firework_phase(bmp_repeat_count= BMP_REPEAT_COUNT * 2)
