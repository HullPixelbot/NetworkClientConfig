

import sys
import glob
import time
import random
from tkinter import *
from tkinter import messagebox
from tkinter import ttk

from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename

try:
    import serial
except(ModuleNotFoundError):
    messagebox.showerror("serial library missing", "Program aborting")
    exit()
        
class NetworkConfig(object):
    '''
    Provides a configuration interface for the
    HullOS network connector. 
    '''
    def clear_output(self):
        self.output_Text.delete('0.0', END)
        self.root.update()

    def serial_port_names(self):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        return ports

    def active_port_names(self):
        
        result = []

        port_names = self.serial_port_names()

        for port_name in port_names:
             port = self.open_connection(port_name)
             if port != None:
                port.close()
                # We found a port - remember it
                result.append(port_name)
        return result

    def set_status(self,status):
        self.status_label.config(text=status)
        self.root.update()

    def set_serial_status_state(self, status):
        if status:
            self.serial_button_frame["bg"] = "green"
        else:
            self.serial_button_frame["bg"] = "red"
        self.root.update()

    def read_line_from_serial(self,ser):
        result = ""
        # Stop the ticker from reading the input
        while True:
            b=ser.read(size=1)
            if len(b)==0:
                # timeout
                return result
            c = chr(b[0])
            if c=='\n':
                return result
            result = result + c

    def send_text(self, text):
        
        if self.serial_port == None:
            self.set_status('Serial port not connected')
            return

        clean_text = ""
        for ch in text:
            if ch != '\n' and ch !='\r':
                clean_text = clean_text + ch
        
        text = clean_text.strip()
        text = text + '\r'
        return_text = new_numbers_lambda = map(lambda x : x if x != '\n' else '\r', text)

        byte_text = bytearray()
        byte_text.extend(map(ord,return_text))

        print("send line: " + text)
        for ch in byte_text:
            print(ch)

        self.serial_port.write(byte_text)

    def get_client_version(self, serial_port):
        try:
            serial_port.flushInput()
            serial_port.write(b'*IV\r')
            self.comms_active = True
            response = self.read_line_from_serial(serial_port)
            if response.startswith('Network Client '):
                self.comms_active = False
                return response
            else:
                self.comms_active = False
                return None
        except (OSError, serial.SerialException):
            self.comms_active = False
            return None

    def open_connection(self,port_name):
        try:
            port = serial.Serial(port_name, 1200, timeout=1)
        except (OSError, serial.SerialException):
            return None
        return port


    def try_to_connect(self,port_name):

        port = self.open_connection(port_name)

        if port == None:
            self.set_serial_status_state(False)
            return False

        self.set_status('Found port: ' + port_name)
        
        # give the robot time to settle after reset
        time.sleep(1)
        
        version = self.get_client_version(port)
        
        if version != None :
            self.serial_port = port
            self.set_status('Serial port ' + port_name + ' connected to Pixelbot Network Client ' + version)
            self.clear_output()
            self.set_serial_status_state(True)
            return True

        self.set_serial_status_state(False)
        return False
    
    def do_populate_ports_combobox(self):
        if self.serial_port != None:
            self.set_status('Cannot scan while connected')
            return
        port_names = self.active_port_names()
        self.comportComboBox['values']=port_names
        if len(port_names)>0:
            self.comportComboBox.current(0)

    def do_scan_for_serial(self):
        
        if self.serial_port != None:
            self.set_status('Serial port already connected')
            return
        
        self.set_status('Connecting..')

        if self.last_working_port != None:
            if self.try_to_connect(self.last_working_port):
                return

        port_names = self.active_port_names()

        for port_name in port_names:
            if self.try_to_connect(port_name):
                # We found a port - remember it
                self.last_working_port = port_name
                self.force_disconnect = False
                return

        self.set_status('No Devices found')

    def dump_string(self,title, string):
        print(title, string)
        print(title,end='')
        for ch in string:
            print(ord(ch),end='')
        print()

    def do_disconnect_serial(self):
        
        self.set_status('Serial port disconnected')
        
        if self.serial_port == None:
            return

        self.serial_port.close()

        self.serial_port = None
        self.force_disconnect = True
        self.set_serial_status_state(False)

    def update_output_text(self):
        if self.serial_port != None:
            try:
                while self.serial_port.in_waiting > 0:
                    b = self.serial_port.read()
                    c = chr(b[0])
                    self.output_Text.insert(END,c)
                    self.output_Text.see(END)
            except:
                self.serial_port.close()
                self.serial_port = None
                self.set_status('Serial port disconnected')
                self.set_serial_status_state(False)

    def do_tick(self):

        self.root.after(1000,self.do_tick)

        # stop the output tick display from absorbing
        # characters we want to see
        if self.comms_active:
            return
        
        if self.serial_port == None:
            if not self.force_disconnect:
                # Only try to reconnect if the user
                # hasn't forced a disconnection
                if self.last_working_port != None:
                    # We have been unplugged - try to reconnect
                    self.serial_port = self.open_connection(self.last_working_port)
                    if self.serial_port != None:
                        self.set_status('Serial port reconnected')
                        self.set_serial_status_state(True)
        
        if self.serial_port != None:
            try:
                while self.serial_port.in_waiting > 0:
                    b = self.serial_port.read()
                    c = chr(b[0])
                    self.output_Text.insert(END,c)
                    self.output_Text.see(END)
            except:
                self.serial_port.close()
                self.serial_port = None
                self.set_status('Serial port disconnected')
                self.set_serial_status_state(False)

    def do_save_settings(self):
        if not self.check_serial_port():
            return
        try:
            self.serial_port.flushInput()
            self.serial_port.write(b'*NS\r')
            self.comms_active = True
            for i in range(0, self.no_of_wifi_configs):
                self.send_text(self.accessPoints[i].get('1.0',END))
                self.send_text(self.passwords[i].get('1.0',END))

            self.send_text(self.devicename_text.get('1.0',END))
            self.send_text(self.mqtt_username_text.get('1.0',END))
            self.send_text(self.host_address_text.get('1.0',END))
            self.send_text(self.key_text.get('1.0',END))

            self.set_status('Settings saved')

        except (OSError, serial.SerialException):
            self.set_status('Settings load failed')
        self.comms_active = False

    def do_load_settings(self):
        if not self.check_serial_port():
            return
        try:
            self.serial_port.flushInput()
            # Send the command to read the settings from the remote client
            self.serial_port.write(b'*NR\r')
            self.comms_active = True
            for i in range(0, self.no_of_wifi_configs):
                self.accessPoints[i].delete('0.0', END)
                self.accessPoints[i].insert('0.0', self.read_line_from_serial(self.serial_port))
                self.passwords[i].delete('0.0', END)
                self.passwords[i].insert('0.0', self.read_line_from_serial(self.serial_port))

            self.devicename_text.delete('0.0', END)
            self.devicename_text.insert('0.0', self.read_line_from_serial(self.serial_port))

            self.mqtt_username_text.delete('0.0', END)
            self.mqtt_username_text.insert('0.0', self.read_line_from_serial(self.serial_port))

            self.host_address_text.delete('0.0', END)
            self.host_address_text.insert('0.0', self.read_line_from_serial(self.serial_port))

            self.key_text.delete('0.0', END)
            self.key_text.insert('0.0', self.read_line_from_serial(self.serial_port))

            self.set_status('Settings loaded')

        except (OSError, serial.SerialException):
            self.set_status('Settings load failed')
        self.comms_active = False

    def check_serial_port(self):
        if self.serial_port==None:
            self.set_status('Not connected to a device')
            return False
        return True

    def do_scan_access_points(self):
        if self.check_serial_port():
            self.serial_port.write(b'*NA\r')

    def do_connect_to_network(self):
        if self.check_serial_port():
            self.serial_port.write(b'*NC\r')

    def do_list_settings(self):
        if self.check_serial_port():
            self.serial_port.write(b'*NR\r')

    def do_preset_settings(self):
        if self.check_serial_port():
            self.serial_port.write(b'*ND\r')

    def do_direct_connect(self):
        port_name=self.comportComboBox.get()
        self.try_to_connect(port_name)
        pass
           
    def __init__(self,root):
        '''
        Create an instance of the editor. root provides
        the Tkinter root frame for the editor
        '''

        self.root = root
        
        self.no_of_wifi_configs = 5

        Grid.rowconfigure(self.root, 0, weight=1)
        Grid.columnconfigure(self.root, 0, weight=1)

        self.root.title("HullOS Network Configuration 1.0 Rob Miles")

        self.serial_port = None
        self.last_working_port = None
        self.force_disconnect = False
        self.comms_active=False

        # used to detect when to save
        self.code_copy = ""
        
        self.frame = Frame(root,borderwidth=5)
        Grid.rowconfigure(self.frame, 0, weight=1)
        Grid.columnconfigure(self.frame, 1, weight=1)

        rowCount = 0
        
        self.frame.grid(row=rowCount,column=0, padx=5, pady=5,sticky='nsew')
        rowCount = rowCount + 1

        devicename_label = Label(self.frame,text='Device name: ');
        devicename_label.grid(sticky=E+N+S, row=rowCount, column=0, padx=5, pady=5)

        self.accessPoints = []
        self.passwords = []
        
        wifi_frame = Frame(self.frame)
        
        for wifi_count in range(0,self.no_of_wifi_configs):
            wifi_label = Label(wifi_frame,text='Access Point: ');
            wifi_label.grid(sticky=E+N+S+W, row=wifi_count, column=0, padx=5, pady=5)
            wifi_text = Text(wifi_frame, width=20, height=1)
            wifi_text.grid(sticky=E+N+S+W, row=wifi_count, column=1, padx=5, pady=5)
            self.accessPoints.append(wifi_text)

            password_label = Label(wifi_frame,text='Password: ');
            password_label.grid(sticky=E+N+S+W, row=wifi_count, column=2, padx=5, pady=5)
            password_text = Text(wifi_frame, width=20, height=1)
            password_text.grid(sticky=E+N+S+W, row=wifi_count, column=3, padx=5, pady=5)
            self.passwords.append(password_text)

        wifi_frame.grid(row=rowCount, column=0, padx=5, pady=5, columnspan=2,sticky='nsew')
        rowCount = rowCount + 1

        devicename_label = Label(self.frame,text='Device name: ')
        devicename_label.grid(sticky=E+N+S, row=rowCount, column=0, padx=5, pady=5)
        self.devicename_text = Text(self.frame, width=20, height=1)
        self.devicename_text.grid(sticky=E+N+S+W, row=rowCount, column=1, padx=5, pady=5)
        rowCount = rowCount + 1
        
        mqtt_username_label = Label(self.frame,text='MQTT username: ')
        mqtt_username_label.grid(sticky=E+N+S, row=rowCount, column=0, padx=5, pady=5)
        self.mqtt_username_text = Text(self.frame, width=20, height=1)
        self.mqtt_username_text.grid(sticky=E+N+S+W, row=rowCount, column=1, padx=5, pady=5)
        rowCount = rowCount + 1

        host_address_label = Label(self.frame,text='Host: ');
        host_address_label.grid(sticky=E+N+S, row=rowCount, column=0, padx=5, pady=5)
        self.host_address_text = Text(self.frame, width=20, height=1)
        self.host_address_text.grid(sticky=E+N+S+W, row=rowCount, column=1, padx=5, pady=5)
        rowCount = rowCount + 1
        
        key_label = Label(self.frame,text='Key: ');
        key_label.grid(sticky=E+N+S, row=rowCount, column=0, padx=5, pady=5)
        self.key_text = Text(self.frame, width=20, height=1)
        self.key_text.grid(sticky=E+N+S+W, row=rowCount, column=1, padx=5, pady=5)
        rowCount = rowCount + 1
        
        output_label = Label(self.frame,text='Output:')
        output_label.grid(sticky=E+N, row=rowCount, column=0, padx=5, pady=5)

        self.output_Text = Text(self.frame, height=5)
        self.output_Text.grid(row=rowCount, column=1, padx=5, pady=5, sticky='nsew')

        output_Scrollbar = Scrollbar(self.frame, command=self.output_Text.yview)
        output_Scrollbar.grid(row=rowCount, column=2, sticky='nsew')
        self.output_Text['yscrollcommand'] = output_Scrollbar.set

        rowCount = rowCount + 1
       
        program_button_frame = Frame(self.frame)

        saveButton = Button(program_button_frame, text='Save Settings', command=self.do_save_settings)
        saveButton.grid(sticky='nsew', row=0, column=0, padx=5, pady=5)

        loadButton = Button(program_button_frame, text='Load Settings', command=self.do_load_settings)
        loadButton.grid(sticky='nsew', row=0, column=1, padx=5, pady=5)

        scanButton = Button(program_button_frame, text='List access points', command=self.do_scan_access_points)
        scanButton.grid(sticky='nsew', row=0, column=2, padx=5, pady=5)

        connectToNetworkButton = Button(program_button_frame, text='Connect to network', command=self.do_connect_to_network)
        connectToNetworkButton.grid(sticky='nsew', row=0, column=3, padx=5, pady=5)

        listSettingsButton = Button(program_button_frame, text='List settings', command=self.do_list_settings)
        listSettingsButton.grid(sticky='nsew', row=0, column=4, padx=5, pady=5)

#        presetSettingsButton = Button(program_button_frame, text='Preset settings', command=self.do_preset_settings)
#        presetSettingsButton.grid(sticky='nsew', row=0, column=5, padx=5, pady=5)

        program_button_frame.grid(row=rowCount, column=0, padx=5, pady=5, columnspan=2)
        rowCount = rowCount + 1

        self.serial_button_frame = Frame(self.frame)

        scanSerialButton = Button(self.serial_button_frame, text='Scan', command=self.do_populate_ports_combobox)
        scanSerialButton.grid(sticky='nsew', row=0, column=0, padx=5, pady=5)

        self.comportComboBox = ttk.Combobox(self.serial_button_frame, textvariable='None')
        self.comportComboBox['values']=('Press_Scan')
        self.comportComboBox.grid(sticky='nsew', row=0, column=1, padx=5, pady=5)

        connectSerialButton = Button(self.serial_button_frame, text='Connect', command=self.do_direct_connect)
        connectSerialButton.grid(sticky='nsew', row=0, column=2, padx=5, pady=5)

        disconnectSerialButton = Button(self.serial_button_frame, text='Disconnect', command=self.do_disconnect_serial)
        disconnectSerialButton.grid(sticky='nsew', row=0, column=3, padx=5, pady=5)
        
        self.serial_button_frame.grid(row=rowCount, column=0, padx=5, pady=5, columnspan=2)
        rowCount = rowCount+1

        self.status_label = Label(self.frame,text="Status")
        self.status_label.grid(row=rowCount, column=0, columnspan=5,sticky='nsew')

        root.update()
        # now root.geometry() returns valid size/placement
        root.minsize(root.winfo_width(), root.winfo_height())        

        self.do_tick()

        self.do_populate_ports_combobox()

#        self.do_connect_serial()

root=Tk()
editor=NetworkConfig(root)
root.mainloop()

