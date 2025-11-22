import pillow_heif
print("Saver available:", hasattr(pillow_heif, "register_heif_saver"))
print("Supported write formats:", pillow_heif.get_supported_write_formats())
