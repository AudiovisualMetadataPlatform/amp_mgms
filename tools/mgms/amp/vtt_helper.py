import time


# Get the header of the vtt file
def get_header():
    return "WEBVTT"+"\n"
                
# Get a new line of the vtt text
def get_line(speaker, text):    
    return "<v "+speaker+">"+text+"\n" if speaker else text+"\n"

# Get an empty line to the vtt output
def get_empty_line():
    return "\n"

# Get a time entry to the vtt output
def get_time(start_time, end_time):
    return str(convert(start_time))+" --> "+str(convert(end_time))+"\n"
    
# Convert seconds to HH:MM:SS
def convert(seconds): 
    return time.strftime("%H:%M:%S", time.gmtime(seconds)) 
   
