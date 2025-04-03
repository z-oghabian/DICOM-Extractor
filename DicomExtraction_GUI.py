import os
import shutil
import pydicom
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

# Function to select folders using GUI
def select_folder(title):
    folder = filedialog.askdirectory(title=title)
    return folder if folder else None

# Function to sanitize folder names (preserving dots and numbers)
def sanitize_filename(name):
    if not isinstance(name, str):
        return "Unknown"
    return re.sub(r'[<>:"/\\|?*]', '_', name)  # Only replaces forbidden characters

# Function to check available disk space dynamically
def check_disk_space(output_dir, required_space):
    total, used, free = shutil.disk_usage(output_dir)
    return free, free >= required_space

# Function to reset GUI elements
def reset_gui(input_var, output_var, progress_var, status_label):
    input_var.set("")
    output_var.set("")
    progress_var.set(0)
    status_label.config(text="Waiting for input...")

# Function to process DICOM files
def process_dicoms(input_dir, output_dir, progress_var, progress_bar, status_label, input_var, output_var):
    patient_dict = {}
    total_files = sum(len(files) for _, _, files in os.walk(input_dir))
    estimated_size = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(input_dir) for f in files)
    #estimated_size = total_files * 2 * 1024 * 1024  # Estimating each DICOM file to be ~2MB
    
    free_space, has_space = check_disk_space(output_dir, estimated_size)
    if not has_space:
        messagebox.showerror("Insufficient Space", f"Not enough disk space to proceed. Required: {estimated_size // (1024 * 1024)} MB, Available: {free_space // (1024 * 1024)} MB")
        return
    
    processed_files = 0
    
    for root_dir, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root_dir, file)
            
            try:
                dicom_data = pydicom.dcmread(file_path, stop_before_pixels=True)
                patient_name = sanitize_filename(str(getattr(dicom_data, "PatientName", "Unknown")))
                patient_id = sanitize_filename(str(getattr(dicom_data, "PatientID", "0000")))
                patient_folder = f"{patient_name}_{patient_id}".replace(" ", "_")
                series_name = sanitize_filename(str(getattr(dicom_data, "SeriesDescription", f"Unknown_Series_{dicom_data.SeriesInstanceUID}")))
                instance_number = getattr(dicom_data, "InstanceNumber", len(patient_dict.get(patient_folder, {}).get(series_name, [])) + 1)
                
                patient_dict.setdefault(patient_folder, {}).setdefault(series_name, []).append((instance_number, file_path))
            except Exception as e:
                messagebox.showwarning("File Skipped", f"Skipping {file}: {e}")
                continue
            
            processed_files += 1
            progress_var.set((processed_files / total_files) * 100)
            progress_bar.update()
    
    for patient_folder, series_dict in patient_dict.items():
        patient_dir = os.path.join(output_dir, patient_folder)
        os.makedirs(patient_dir, exist_ok=True)
        
        for series_name, files in series_dict.items():
            files.sort(key=lambda x: x[0])
            series_dir = os.path.join(patient_dir, series_name)
            os.makedirs(series_dir, exist_ok=True)
            
            for i, (_, file_path) in enumerate(files, start=1):
                new_file_name = f"Img{str(i).zfill(5)}.dcm"
                shutil.copy2(file_path, os.path.join(series_dir, new_file_name))
    
    progress_var.set(100)
    progress_bar.update()
    messagebox.showinfo("Processing Complete", "All files have been sorted successfully!")
    status_label.config(text="Processing Complete")
    reset_gui(input_var, output_var, progress_var, status_label)
    
# GUI Setup
def main():
    root = tk.Tk()
    root.title("DICOM Sorter")
    root.geometry("400x300")
    
    tk.Label(root, text="Select Input Folder:").pack(pady=5)
    input_var = tk.StringVar()
    input_btn = tk.Button(root, text="Browse", command=lambda: input_var.set(select_folder("Select DICOM Folder")))
    input_btn.pack()
    tk.Label(root, textvariable=input_var, wraplength=380).pack()
    
    tk.Label(root, text="Select Output Folder:").pack(pady=5)
    output_var = tk.StringVar()
    output_btn = tk.Button(root, text="Browse", command=lambda: output_var.set(select_folder("Select Output Folder")))
    output_btn.pack()
    tk.Label(root, textvariable=output_var, wraplength=380).pack()
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, length=300)
    progress_bar.pack(pady=10)
    
    status_label = tk.Label(root, text="Waiting for input...")
    status_label.pack()
    
    process_btn = tk.Button(root, text="Start Sorting", command=lambda: process_dicoms(input_var.get(), output_var.get(), progress_var, progress_bar, status_label, input_var, output_var))
    process_btn.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()
