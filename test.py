import wmi

c = wmi.WMI()

# Запрашиваем информацию о материнской плате (BaseBoard)
for board in c.Win32_BaseBoard():
    print(f"Производитель: {board.Manufacturer}")
    print(f"Модель: {board.Product}")  # Модель обычно хранится в Product