# Review Sistem PKL Sains Data

## Kekuatan
- **Konfigurasi dapat dikustomisasi lewat environment**: koneksi database, secret key, dan batasan ukuran surat penerimaan diambil dari variabel environment sehingga mudah dipindah antar lingkungan (dev/staging/prod).【F:backend/pkl_backend/settings.py†L25-L149】
- **Model master data sudah memetakan aktor utama PKL**: ada representasi `Dosen`, `Mitra`, `PeriodePKL`, `Mahasiswa`, hingga `PendaftaranPKL` dengan relasi dan help text yang jelas untuk kebutuhan bisnis PKL.【F:backend/masterdata/models.py†L41-L260】
- **Validasi file surat penerimaan disiapkan**: validator khusus membatasi ekstensi PDF dan ukuran maksimal berbasis konfigurasi, mengurangi risiko unggahan tidak valid.【F:backend/masterdata/models.py†L15-L37】

## Risiko / Temuan
- **SECRET_KEY fallback hard-coded**: ada default secret key untuk dev yang akan dipakai jika variabel environment tidak diset; jika tidak dioverride di produksi, aplikasi rentan (session & signing bisa ditembus).【F:backend/pkl_backend/settings.py†L25-L33】
- **DEBUG default True**: kondisi ini membuat error page detail terbuka jika environment tidak diset dengan benar; perlu memastikan DJANGO_DEBUG disetel False di produksi.【F:backend/pkl_backend/settings.py†L32-L34】
- **ALLOWED_HOSTS kosong secara default**: ketika DJANGO_ALLOWED_HOSTS tidak diset, daftar host kosong dapat menolak request di deployment standar; sebaiknya tetapkan default minimal atau panduan konfigurasi jelas.【F:backend/pkl_backend/settings.py†L36-L40】
- **Model portal belum diisi**: `backend/portal/models.py` masih kosong sehingga fitur portal belum memiliki struktur data; akan menghambat pengembangan API/view yang konsisten.【F:backend/portal/models.py†L1-L4】
- **Ruang uji otomatis belum jelas dieksekusi**: meski ada berkas `backend/portal/tests.py`, tidak ada dokumentasi atau konfigurasi CI yang memastikan suite ini berjalan; beberapa pengujian mengandalkan model yang belum diimplementasi penuh sehingga berpotensi gagal saat dijalankan.【F:backend/portal/tests.py†L1-L504】

## Rekomendasi
1. Wajibkan konfigurasi penting di environment produksi: set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, dan `DJANGO_ALLOWED_HOSTS` sesuai domain/hostname deployment; pertimbangkan validasi start-up yang gagal jika variabel tidak ada.【F:backend/pkl_backend/settings.py†L25-L40】
2. Lengkapi model portal sesuai kebutuhan (misal entitas logbook, seminar, atau penjadwalan bimbingan) agar rute dan form yang sudah ada dapat beroperasi dengan database schema yang jelas.【F:backend/portal/models.py†L1-L4】
3. Tambahkan pipeline CI sederhana (mis. GitHub Actions) yang menjalankan `python manage.py test` sehingga regresi langsung terdeteksi; rapikan/kelompokkan kasus uji agar sesuai implementasi model terkini.【F:backend/portal/tests.py†L1-L504】
