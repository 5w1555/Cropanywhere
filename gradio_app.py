import os
import tempfile
import shutil
from functools import lru_cache

import gradio as gr
from config import get_preset_labels, key_for_label, get_preset_by_key
from cropper import (
    get_face_and_landmarks,
    auto_crop,
    head_bust_crop,
    apply_aspect_ratio_filter,
    apply_filter,
)

from retinaface.pre_trained_models import get_model
device = "cpu"
_model = get_model("resnet50_2020-07-20", max_size=2048, device=device)
_model.eval()

CUSTOM_CSS = """
body {
    background: radial-gradient(circle at 30% 20%, #0b2b45, #061a2b 60%, #04121e);
    font-family: 'Inter', sans-serif !important;
    color: #e9f3ff;
}
.gradio-container { padding: 0 !important; }
.container-glass {
    width: 950px;
    margin: 60px auto;
    display: flex;
    gap: 40px;
    padding: 40px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: 0 0 30px rgba(0, 160, 255, 0.25);
}
.panel {
    flex: 1;
    padding: 25px;
    border-radius: 15px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: inset 0 0 20px rgba(0, 180, 255, 0.05);
}
.panel-title {
    font-size: 1.4rem;
    font-weight: 500;
    letter-spacing: 1px;
    margin-bottom: 20px;
}
.upload-box {
    border: 2px dashed rgba(0, 200, 255, 0.4);
    border-radius: 12px;
    padding: 50px 10px;
    text-align: center;
    cursor: pointer;
    transition: 0.25s;
    background: rgba(0,0,0,0.1);
}
.upload-box:hover {
    background: rgba(0, 200, 255, 0.08);
    border-color: rgba(0,220,255,0.8);
}
select, .gradio-select select {
    width: 100% !important;
    background: rgba(255,255,255,0.07) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
    padding: 10px !important;
}
input[type="range"] {
    accent-color: #00c2ff !important;
    width: 100% !important;
}
.preview-box {
    width: 100%;
    height: 260px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(0,0,0,0.2);
}
.gradio-button {
    background: linear-gradient(135deg, #00e5ff, #00b3ff) !important;
    color: #00293f !important;
    border-radius: 12px !important;
    padding: 14px 0 !important;
    font-weight: 600 !important;
    border: none !important;
    transition: 0.2s !important;
    box-shadow: 0 0 15px rgba(0, 195, 255, 0.4);
}
.gradio-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 20px rgba(0, 235, 255, 0.6);
}
"""

def parse_ratio(r):
    if isinstance(r, str):
        if r.lower() == "none": return None
        if ":" in r:
            w, h = r.split(":", 1)
            try: return float(w)/float(h)
            except: return None
        try: return float(r)
        except: return None
    if isinstance(r, (int,float)): return float(r)
    return None

from PIL import Image, ImageOps

@lru_cache(maxsize=16)
def cached_preview(img_path, preset_label, margin, ratio, filter_name, intensity, rotate):
    key = key_for_label(preset_label)
    method = "headbust" if key=="headbust" else "auto"
    if method=="headbust":
        cropped = head_bust_crop(img_path, int(margin), ratio, 0.3)
    else:
        box, lm, cv, pil, meta = get_face_and_landmarks(img_path,0.3,rotate,_model)
        if box is None: return None, "❌ No face detected."
        cropped = auto_crop(pil,int(margin),int(margin),box,lm,meta)
        if ratio and cropped: cropped = apply_aspect_ratio_filter(cropped, ratio)
    if cropped is None: return None, "❌ Crop failed."
    return apply_filter(cropped, filter_name, intensity), "✅ Preview generated."

def generate_preview(preset_label,input_files,margin,filter_name,intensity,aspect_ratio,rotate):
    if not input_files: return None,None,"❌ No files uploaded."
    img_path = input_files[0].name
    try:
        before = ImageOps.exif_transpose(Image.open(img_path))
        before.thumbnail((720,720))
    except Exception as e:
        return None,None,f"❌ Failed to load original: {e}"
    ratio = parse_ratio(aspect_ratio)
    after, msg = cached_preview(img_path,preset_label,margin,ratio,filter_name,intensity,rotate)
    if after: after.thumbnail((720,720))
    return before,after,msg

def process_images_with_progress(preset_label,input_files,margin,filter_name,intensity,aspect_ratio,rotate,progress=gr.Progress()):
    if not input_files:
        return "❌ No files uploaded.",None,"0/0 images processed"
    key = key_for_label(preset_label)
    method = "headbust" if key=="headbust" else "auto"
    ratio = parse_ratio(aspect_ratio)
    tmp = tempfile.mkdtemp(prefix="cropped_")
    cnt=0
    tot=len(input_files)
    progress(0,"Starting...")
    for i,f in enumerate(input_files):
        img=f.name
        progress(i/tot, f"Processing {i+1}/{tot}")
        if method=="headbust":
            bust=head_bust_crop(img,int(margin),ratio,0.3)
        else:
            box,lm,cv,pil,meta = get_face_and_landmarks(img,0.3,rotate,_model)
            if box is None: continue
            bust=auto_crop(pil,int(margin),int(margin),box,lm,meta)
            if ratio and bust: bust=apply_aspect_ratio_filter(bust,ratio)
        if bust is None: continue
        out=apply_filter(bust,filter_name,intensity)
        name,ext=os.path.splitext(os.path.basename(img))
        out.save(os.path.join(tmp,f"{name}_cropped{ext}"))
        cnt+=1
    progress(1.0,"Zipping...")
    if cnt==0:
        shutil.rmtree(tmp)
        return "❌ No faces detected.",None,f"0/{tot}"
    zip_path=shutil.make_archive(tmp,'zip',tmp)
    return f"✅ Processed {cnt}/{tot}!",zip_path,f"{cnt}/{tot}"

with gr.Blocks(css=CUSTOM_CSS, theme=None, title="CropAnywhere") as demo:

    with gr.Row(elem_classes="container-glass"):

        with gr.Column(elem_classes="panel"):

            gr.HTML("<div class='panel-title'>Crop Settings</div>")

            preset_dd = gr.Dropdown(
                choices=get_preset_labels(),
                value=(get_preset_labels()[0] if get_preset_labels() else None),
                label="Preset"
            )

            input_files = gr.File(
                label="Drop File Here or Click to Upload",
                file_count="multiple",
                elem_classes=["upload-box"],
                file_types=[".jpg",".jpeg",".png",".webp",".bmp",".tiff",".heic",".heif"]
            )

            margin = gr.Slider(0,100,value=30,label="Margin")

            aspect_ratio = gr.Dropdown(
                choices=[None,1.0,4/5,1.91,9/16,3/2,5/4,16/9],
                value=None,
                label="Aspect Ratio"
            )

            rotate = gr.Checkbox(label="Auto-Rotate",value=True)

            gr.HTML("<div class='panel-title' style='margin-top:20px'>Visual Effects</div>")

            filter_name = gr.Dropdown(
                ["None","Brightness","Contrast","Blur","Edge Detection","Sepia"],
                "None", label="Filter"
            )

            intensity = gr.Slider(0,100,value=50,label="Intensity")

            with gr.Row():
                preview_btn = gr.Button("Preview")
                process_btn = gr.Button("Process All")

        with gr.Column(elem_classes="panel"):

            gr.HTML("<div class='panel-title'>Before & After</div>")

            comparison_gallery = gr.Gallery(
                columns=2, rows=1,
                object_fit="contain",
                height="300px"
            )

            status = gr.Textbox(label="Status",interactive=False)
            progress_info = gr.Textbox(label="Progress",interactive=False)
            download_zip = gr.File(label="Download")

    def apply_preset(label):
        cfg=get_preset_by_key(key_for_label(label))
        return cfg.get("margin",30),parse_ratio(cfg.get("target_ratio",None))

    def enhanced_preview(preset_label,input_files,margin,filter_name,intensity,aspect_ratio,rotate):
        b,a,msg=generate_preview(preset_label,input_files,margin,filter_name,intensity,aspect_ratio,rotate)
        return ([b,a] if b and a else []), msg

    preset_dd.change(apply_preset,preset_dd,[margin,aspect_ratio])

    preview_btn.click(
        enhanced_preview,
        [preset_dd,input_files,margin,filter_name,intensity,aspect_ratio,rotate],
        [comparison_gallery,status]
    )

    process_btn.click(
        process_images_with_progress,
        [preset_dd,input_files,margin,filter_name,intensity,aspect_ratio,rotate],
        [status,download_zip,progress_info]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0",server_port=7860,debug=True,share=True)
