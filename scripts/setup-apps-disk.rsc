# Setup disk kedua untuk RouterOS Apps (/app)
# Jalankan setelah disk Apps terdeteksi di /disk

# Format disk Apps (biasanya muncul sebagai disk1 setelah attach virtio kedua)
:local diskName "disk1"

:if ([:len [/disk find where name=$diskName]] = 0) do={
  :put "ERROR: disk '$diskName' tidak ditemukan. Cek /disk print"
} else={
  :put "Formatting $diskName as ext4..."
  /disk format-drive $diskName file-system=ext4

  :delay 3s
  /disk print detail

  # Pastikan container package aktif
  /system package enable container

  # Assign disk ke App settings
  /app settings set disk=$diskName

  :put "App disk configured. Jalankan /app setup di Winbox/Terminal untuk menyelesaikan wizard."
  /app settings print
}
