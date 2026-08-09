import os
import customtkinter as ctk
import libs.cfg_handle as cfg_handle

class WelcomePage:
    def __init__(self, parent, new_file_callback, open_file_callback, open_folder_callback, 
                 open_recent_callback, toggle_welcome_callback):
        self.parent = parent
        self.new_file_callback = new_file_callback
        self.open_file_callback = open_file_callback
        self.open_folder_callback = open_folder_callback
        self.open_recent_callback = open_recent_callback
        self.toggle_welcome_callback = toggle_welcome_callback
        self.welcome_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e")
        self._create_welcome_page()
    
    def _create_welcome_page(self):
        card = ctk.CTkFrame(self.welcome_frame, fg_color="#2d2d2d", corner_radius=10)
        card.place(relx=0.5, rely=0.4, anchor="center")

        title = ctk.CTkLabel(card, text="Thon Code", font=("微软雅黑", 28, "bold"))
        title.pack(pady=(30, 10))

        subtitle = ctk.CTkLabel(card, text="开始编写代码", font=("微软雅黑", 14))
        subtitle.pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="新建文件", width=150, command=self.new_file_callback).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="打开文件...", width=150, command=self.open_file_callback).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="打开文件夹", width=150, command=self.open_folder_callback).pack(side="left", padx=10)

        recent_label = ctk.CTkLabel(card, text="最近打开", font=("微软雅黑", 12), anchor="w")
        recent_label.pack(pady=(20, 5), padx=20, anchor="w")

        # 从配置读取最近项目
        recent_projects = cfg_handle.cfg_handle().get_recent_projects()
        if recent_projects:
            for proj in recent_projects[:5]:
                btn = ctk.CTkButton(card, text=os.path.basename(proj), fg_color="transparent",
                                    command=lambda path=proj: self.open_recent_callback(path))
                btn.pack(pady=2, padx=20, anchor="w")
        else:
            no_recent = ctk.CTkLabel(card, text="暂无最近项目", font=("微软雅黑", 10), text_color="gray")
            no_recent.pack(pady=5, padx=20, anchor="w")

        config_frame = ctk.CTkFrame(card, fg_color="transparent")
        config_frame.pack(pady=(20, 30))

        self.welcome_show_check = ctk.CTkCheckBox(config_frame, text="每次启动显示欢迎页",
                                                  command=self.toggle_welcome_callback)
        self.welcome_show_check.select()
    
    def get_frame(self):
        return self.welcome_frame
    
    def get_checkbox(self):
        return self.welcome_show_check
    
    def set_checkbox_state(self, state):
        if state:
            self.welcome_show_check.select()
        else:
            self.welcome_show_check.deselect()
    
    def place(self, **kwargs):
        self.welcome_frame.place(**kwargs)
    
    def place_forget(self):
        self.welcome_frame.place_forget()