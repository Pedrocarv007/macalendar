"""Operações gráficas partilhadas pelos modelos de documentos."""


def apply_rounded_corners(image, radius=50):
    from PIL import Image, ImageDraw

    image = image.convert("RGBA")
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    image.putalpha(mask)
    return image


def paste_photo(background, photo_image, cx, cy, offset_y=-50):
    from PIL import Image, ImageDraw, ImageOps

    resampling = getattr(Image, "Resampling", Image)
    photo = ImageOps.fit(
        photo_image.convert("RGBA"),
        (621, 834),
        method=resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    photo = apply_rounded_corners(photo, radius=50)

    border = ImageDraw.Draw(photo)
    border.rounded_rectangle(
        [(0, 0), (620, 833)],
        radius=50,
        outline="white",
        width=10,
    )

    x = cx - 621 // 2
    y = cy - 800 // 2 + offset_y
    background.paste(photo, (x, y), mask=photo)
