from PIL import Image, ImageDraw, ImageFont

# Carregar o fundo
aniversario = Image.open("aniversarios.png").convert("RGBA")
fundo = Image.open("fundo.png").convert("RGBA")


# Obter dimensões
largura, altura = fundo.size

centro_x = largura // 2
centro_y = altura // 2


# Carregar e redimensionar a foto
foto = Image.open("2.png").resize((621, 834)).convert("RGBA")


def aplicar_bordas_arredondadas(imagem, raio):
    # Garante que a imagem tenha canal alfa (transparência)
    imagem = imagem.convert("RGBA")

    # Criar máscara com mesma dimensão
    mask = Image.new("L", imagem.size, 0)
    draw = ImageDraw.Draw(mask)

    # Desenhar um retângulo com cantos arredondados
    draw.rounded_rectangle([(0, 0), imagem.size], radius=raio, fill=255)

    # Aplicar a máscara à imagem (preserva somente a área dentro do shape)
    imagem.putalpha(mask)

    return imagem

foto_arredondada = aplicar_bordas_arredondadas(foto, raio=50)


fundo.paste(foto_arredondada, (centro_x - 621 // 2, centro_y - 800 // 2-50), mask=foto_arredondada)
aniversario.paste(foto_arredondada, (centro_x - 621 // 2, centro_y - 800 // 2-50), mask=foto_arredondada)
# Adicionar textos
draw = ImageDraw.Draw(fundo)
fonte_nome = ImageFont.truetype("arial.ttf", 60)
fonte_data = ImageFont.truetype("arial.ttf", 55)

# Nome e data (você pode trocar esses valores em loop)
nome = "oi"
data = "07/10/2025"


xmin_mome, ymin_nome, xmax_nome, ymax_nome = fonte_nome.getbbox(nome)

xmin_data, ymin_data, xmax_data, ymax_data = fonte_data.getbbox(data)

largura_nome = xmax_nome - xmin_mome
largura_data = xmax_data - xmin_data
# Escrever o nome (ajuste a posição)
draw.text((centro_x - largura_nome // 2, centro_y + 400), nome, font=fonte_nome, fill="white")

# Escrever a data
draw.text((centro_x - largura_data // 2, centro_y + 505), data, font=fonte_data, fill="white")


draw_aniversario = ImageDraw.Draw(aniversario)
# Escrever o nome (ajuste a posição)
draw_aniversario.text((centro_x - largura_nome // 2, centro_y + 400), nome, font=fonte_nome, fill="white")
# Escrever a data
draw_aniversario.text((centro_x - largura_data // 2, centro_y + 530), data, font=fonte_data, fill="white")


# Salvar imagem final
fundo.save("cartao_bem_vindo.png")
aniversario.save("cartao_aniversario.png")
