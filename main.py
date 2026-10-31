"""
Arcana — Ruang Tarot
====================

Aplikasi pembacaan tarot end-to-end berbahasa Indonesia (Streamlit).

Cara menjalankan
----------------
    pip install -r requirements.txt
    streamlit run main.py

Struktur folder
---------------
    main.py
    requirements.txt
    .streamlit/config.toml        (tema gelap; opsional)
    assets/cards/*.jpg            (78 kartu Rider–Waite–Smith)

Penamaan file kartu
-------------------
    m00 – m21  : Major Arcana (The Fool … The World)
    w01 – w14  : Tongkat / Wands
    c01 – c14  : Cawan / Cups
    s01 – s14  : Pedang / Swords
    p01 – p14  : Koin / Pentacles
    01 = As, 02–10 = Dua–Sepuluh, 11 = Page, 12 = Ksatria, 13 = Ratu, 14 = Raja

Ingin memakai hasil ekspor dari Figma? Cukup timpa file di assets/cards
dengan nama yang sama (format .jpg atau .png).
"""

from __future__ import annotations

import base64
import hashlib
import html
import math
import random
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Konfigurasi dasar
# ─────────────────────────────────────────────────────────────────────────────

APP_DIR = Path(__file__).parent
CARD_DIR = APP_DIR / "assets" / "cards"
ZONA_WAKTU = ZoneInfo("Asia/Jakarta")
PELUANG_TERBALIK = 0.3  # peluang sebuah kartu keluar terbalik (jika diaktifkan)

BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

# ─────────────────────────────────────────────────────────────────────────────
# Data kartu
# ─────────────────────────────────────────────────────────────────────────────

SUIT = {
    "w": {
        "nama": "Tongkat", "inggris": "Wands", "elemen": "Api", "warna": "#e0874f",
        "ranah": "semangat, kerja, ambisi, dan kreativitas",
    },
    "c": {
        "nama": "Cawan", "inggris": "Cups", "elemen": "Air", "warna": "#62a9cc",
        "ranah": "perasaan, hubungan, dan intuisi",
    },
    "s": {
        "nama": "Pedang", "inggris": "Swords", "elemen": "Udara", "warna": "#b9c5d8",
        "ranah": "pikiran, komunikasi, konflik, dan keputusan",
    },
    "p": {
        "nama": "Koin", "inggris": "Pentacles", "elemen": "Tanah", "warna": "#86b56f",
        "ranah": "uang, pekerjaan, tubuh, dan hal-hal yang nyata",
    },
}
WARNA_MAJOR = "#d6b46a"

PERINGKAT = {
    1: ("As", "Ace"), 2: ("Dua", "Two"), 3: ("Tiga", "Three"), 4: ("Empat", "Four"),
    5: ("Lima", "Five"), 6: ("Enam", "Six"), 7: ("Tujuh", "Seven"), 8: ("Delapan", "Eight"),
    9: ("Sembilan", "Nine"), 10: ("Sepuluh", "Ten"), 11: ("Page", "Page"),
    12: ("Ksatria", "Knight"), 13: ("Ratu", "Queen"), 14: ("Raja", "King"),
}

MAKNA_ANGKA = {
    1: "awal baru dan potensi murni",
    2: "pilihan, keseimbangan, dan kemitraan",
    3: "pertumbuhan dan kerja sama",
    4: "stabilitas dan fondasi",
    5: "gangguan, ujian, dan perubahan",
    6: "harmoni dan pemulihan",
    7: "evaluasi dan tantangan batin",
    8: "gerak, usaha, dan penguasaan",
    9: "hampir tuntas — buah dari sebuah proses",
    10: "akhir sebuah siklus",
    11: "rasa ingin tahu, belajar, dan kabar",
    12: "aksi dan pergerakan",
    13: "kedewasaan yang mengarah ke dalam; mengasuh",
    14: "kepemimpinan dan kendali yang mengarah ke luar",
}

MAJOR = [
    ("The Fool", "Si Pengelana"), ("The Magician", "Sang Penyihir"),
    ("The High Priestess", "Pendeta Agung"), ("The Empress", "Sang Permaisuri"),
    ("The Emperor", "Sang Kaisar"), ("The Hierophant", "Sang Imam"),
    ("The Lovers", "Sepasang Kekasih"), ("The Chariot", "Kereta Perang"),
    ("Strength", "Kekuatan"), ("The Hermit", "Sang Pertapa"),
    ("Wheel of Fortune", "Roda Nasib"), ("Justice", "Keadilan"),
    ("The Hanged Man", "Orang Tergantung"), ("Death", "Transformasi"),
    ("Temperance", "Keseimbangan"), ("The Devil", "Belenggu"),
    ("The Tower", "Menara"), ("The Star", "Bintang"),
    ("The Moon", "Bulan"), ("The Sun", "Matahari"),
    ("Judgement", "Kebangkitan"), ("The World", "Dunia"),
]

# id: (kata kunci tegak, kata kunci terbalik, makna tegak, makna terbalik, saran)
MAKNA: dict[str, tuple[str, str, str, str, str]] = {
    # ── Major Arcana ─────────────────────────────────────────────────────────
    "m00": ("awal baru, spontan, kepercayaan", "ceroboh, ragu memulai, risiko tanpa pikir",
            "Babak baru dimulai. Kamu diajak melangkah dengan hati terbuka, meski belum tahu semuanya.",
            "Melangkah tanpa persiapan, atau justru terlalu takut untuk memulai.",
            "Percayalah pada perjalanannya, tapi tetap lihat ke mana kakimu melangkah."),
    "m01": ("kemauan, keterampilan, mewujudkan", "manipulasi, potensi tak terpakai",
            "Kamu punya semua alat yang dibutuhkan. Tinggal fokus dan bertindak.",
            "Potensi terbuang, atau kemampuan dipakai untuk mengelabui.",
            "Satukan niat dan tindakan; kamu lebih mampu dari yang kamu kira."),
    "m02": ("intuisi, misteri, kebijaksanaan batin", "mengabaikan intuisi, rahasia",
            "Jawabannya ada di dalam dirimu. Ada hal yang belum terungkap dan perlu didengar dengan tenang.",
            "Suara hati sedang diabaikan, atau ada rahasia yang menghalangi kejelasan.",
            "Diam sejenak dan dengarkan intuisimu sebelum bertindak."),
    "m03": ("kelimpahan, kasih, kesuburan, kreativitas", "ketergantungan, kreativitas mampet",
            "Masa subur bagi ide, hubungan, dan kenyamanan. Sesuatu sedang bertumbuh.",
            "Terlalu sibuk mengurus orang lain, atau kreativitas sedang tersumbat.",
            "Rawat apa yang ingin kamu tumbuhkan dengan sabar dan lembut."),
    "m04": ("struktur, otoritas, stabilitas", "kaku, mengontrol, kurang disiplin",
            "Saatnya membangun struktur, aturan, dan kepemimpinan yang jelas.",
            "Terlalu mengontrol, atau sebaliknya tak punya pegangan sama sekali.",
            "Buat batas dan rencana yang tegas untuk melindungi tujuanmu."),
    "m05": ("tradisi, nilai, guru, institusi", "memberontak, mencari jalan sendiri",
            "Ada pelajaran dari tradisi, mentor, atau aturan yang sudah teruji.",
            "Kamu mempertanyakan aturan lama dan ingin menempuh jalan sendiri.",
            "Cari bimbingan dari orang yang lebih berpengalaman."),
    "m06": ("cinta, keselarasan, pilihan hati", "ketidakselarasan, menghindari pilihan",
            "Hubungan yang selaras, atau pilihan penting yang sesuai dengan nilai-nilaimu.",
            "Ada ketidakcocokan nilai, atau kamu menghindari pilihan yang perlu diambil.",
            "Pilih dengan hati dan dengan nilai yang kamu pegang."),
    "m07": ("tekad, kemenangan, kendali", "kehilangan arah, terlalu memaksa",
            "Dengan tekad dan fokus, kamu bisa mengendalikan arah dan menang.",
            "Arah mulai kabur, atau kendali lepas karena terlalu memaksa.",
            "Tetapkan tujuan, lalu kendalikan dorongan yang saling tarik di dalam dirimu."),
    "m08": ("keberanian, kesabaran, kelembutan yang kuat", "ragu pada diri, emosi meledak",
            "Kekuatan sejati datang dari kesabaran dan kasih, bukan dari paksaan.",
            "Ada keraguan pada diri sendiri, atau emosi yang sulit dikendalikan.",
            "Hadapi dengan lembut; ketenangan adalah kekuatanmu."),
    "m09": ("menyendiri, introspeksi, mencari makna", "terasing, kesepian",
            "Saatnya menepi untuk merenung dan menemukan jawaban dari dalam.",
            "Menyendiri terlalu lama sampai mulai terasa terasing.",
            "Ambil waktu sendiri yang tenang, lalu kembali membawa cahaya yang kamu temukan."),
    "m10": ("perubahan, siklus, momentum", "merasa sial, menahan perubahan",
            "Roda berputar: perubahan datang dan membuka babak baru.",
            "Merasa sial, atau berusaha menahan perubahan yang tak terelakkan.",
            "Ikuti arus perubahan dan siapkan diri untuk memanfaatkan momentumnya."),
    "m11": ("keadilan, kebenaran, sebab-akibat", "tidak adil, menghindari tanggung jawab",
            "Kebenaran dan keputusan yang adil. Apa yang ditabur, itulah yang dituai.",
            "Ada ketidakadilan, atau tanggung jawab atas pilihan sendiri sedang dihindari.",
            "Bersikap jujur dan bertanggung jawab atas keputusanmu."),
    "m12": ("jeda, sudut pandang baru, berserah", "menunda, jalan di tempat",
            "Berhenti sejenak dan melihat dari sudut berbeda membawa pemahaman baru.",
            "Penundaan tanpa makna, atau pengorbanan yang tidak membawa hasil.",
            "Lepaskan kebutuhan untuk mengontrol; lihat dari sisi yang lain."),
    "m13": ("akhir, transformasi, transisi", "menolak perubahan, terjebak",
            "Sesuatu berakhir agar yang baru bisa lahir. Ini kartu transformasi, bukan kematian harfiah.",
            "Ada penolakan untuk melepas sesuatu yang sebenarnya sudah selesai.",
            "Biarkan yang sudah usai pergi dengan hormat."),
    "m14": ("keseimbangan, kesabaran, moderasi", "berlebihan, timpang",
            "Mencampur hal-hal yang berbeda dengan sabar hingga seimbang.",
            "Ada yang berlebihan, atau hidup sedang terasa timpang.",
            "Cari jalan tengah dan jalani pelan-pelan."),
    "m15": ("keterikatan, godaan, pola tak sehat", "melepaskan diri, mulai sadar",
            "Ada keterikatan, kebiasaan, atau hubungan yang membelenggu.",
            "Kamu mulai sadar dan perlahan melepaskan diri dari belenggu itu.",
            "Kenali apa yang mengikatmu; rantainya sering lebih longgar dari yang terasa."),
    "m16": ("guncangan, perubahan mendadak, kebenaran terungkap", "menunda keruntuhan, takut berubah",
            "Struktur yang rapuh runtuh tiba-tiba, membuka ruang untuk membangun sesuatu yang lebih jujur.",
            "Keruntuhan yang perlu terjadi sedang ditunda, atau guncangannya lebih ringan.",
            "Biarkan yang palsu runtuh; bangun lagi di atas fondasi yang benar."),
    "m17": ("harapan, penyembuhan, inspirasi", "putus asa, kurang percaya diri",
            "Setelah badai, datang harapan dan pemulihan.",
            "Harapan meredup, atau kepercayaan pada diri sendiri sedang goyah.",
            "Jaga harapan tetap menyala; pemulihan sedang berlangsung."),
    "m18": ("ilusi, rasa takut, ketidakpastian", "kabut terangkat, kebenaran muncul",
            "Tidak semuanya seperti kelihatannya. Rasa takut dan bayangan bisa menyesatkan.",
            "Kabut mulai terangkat dan kebenaran perlahan terlihat.",
            "Jangan ambil keputusan besar dalam gelap; tunggu kejelasan."),
    "m19": ("sukacita, keberhasilan, kejelasan", "kebahagiaan tertunda, terlalu optimis",
            "Masa cerah: keberhasilan, kegembiraan, dan kejelasan.",
            "Kebahagiaan sedikit tertutup awan, atau harapan dipasang terlalu tinggi.",
            "Tunjukkan dirimu dan nikmati kehangatan yang ada."),
    "m20": ("kebangkitan, panggilan, refleksi", "menghakimi diri, menolak panggilan",
            "Panggilan untuk bangkit, mengevaluasi diri, dan memulai lembaran baru.",
            "Terlalu keras menghakimi diri sendiri sampai takut melangkah.",
            "Maafkan masa lalumu dan jawab panggilan hidupmu."),
    "m21": ("selesai, utuh, pencapaian", "belum tuntas, tertunda",
            "Sebuah siklus selesai dengan utuh. Kamu telah sampai.",
            "Masih ada yang perlu dituntaskan sebelum bisa melangkah lebih jauh.",
            "Rayakan penyelesaian ini sebelum memulai perjalanan berikutnya."),
    # ── Tongkat / Wands ──────────────────────────────────────────────────────
    "w01": ("inspirasi, awal baru, semangat", "tertunda, kurang arah, ragu memulai",
            "Percikan ide atau peluang baru muncul dengan energi besar untuk memulai.",
            "Semangatnya ada, tapi belum menemukan arah, atau rencana tertunda karena ragu.",
            "Ambil langkah pertama yang kecil hari ini, selagi apinya masih menyala."),
    "w02": ("perencanaan, visi, keputusan", "takut keluar zona nyaman, rencana kabur",
            "Kamu sedang menimbang langkah ke depan dan melihat dunia yang lebih luas.",
            "Rencana macet karena takut melangkah, atau terlalu nyaman dengan yang ada.",
            "Tuliskan rencanamu secara konkret dan tentukan satu langkah pertama."),
    "w03": ("ekspansi, menunggu hasil, pandangan jauh", "hambatan rencana, hasil lambat",
            "Usaha yang sudah dimulai mulai berkembang; saatnya memperluas wawasan.",
            "Hasil belum datang seperti harapan, atau ada kendala yang perlu dibereskan.",
            "Bersabar sambil menyiapkan langkah lanjutan."),
    "w04": ("perayaan, rumah, pencapaian", "ketegangan di rumah, masa transisi",
            "Ada momen syukur dan perayaan; fondasi yang kamu bangun mulai terasa kokoh.",
            "Suasana rumah atau komunitas kurang harmonis, atau sedang dalam masa peralihan.",
            "Rayakan pencapaian kecil bersama orang-orang terdekat."),
    "w05": ("persaingan, gesekan, perbedaan", "menghindari konflik, mereda",
            "Ada gesekan, persaingan, atau terlalu banyak suara yang ingin didengar.",
            "Konflik mereda, atau kamu terlalu menghindari perbedaan pendapat.",
            "Bedakan pertarungan yang penting dari yang hanya menguras energi."),
    "w06": ("kemenangan, pengakuan, percaya diri", "kurang dihargai, haus pujian",
            "Kerja kerasmu mendapat pengakuan; ada kemenangan yang layak dibanggakan.",
            "Merasa kurang dihargai, atau terlalu bergantung pada pujian orang lain.",
            "Akui keberhasilanmu tanpa perlu menunggu tepuk tangan."),
    "w07": ("bertahan, mempertahankan posisi, berani", "kewalahan, tergoda menyerah",
            "Kamu perlu mempertahankan pendirian di tengah tekanan atau tantangan.",
            "Mulai kewalahan dan tergoda menyerah, atau malah terlalu defensif.",
            "Pegang prinsipmu, tapi pilih medan yang benar-benar perlu dibela."),
    "w08": ("gerak cepat, kabar, kemajuan", "tertunda, terburu-buru, salah paham",
            "Segalanya bergerak cepat: kabar, perjalanan, atau perkembangan yang ditunggu.",
            "Ada penundaan, atau keputusan yang diambil terlalu tergesa-gesa.",
            "Manfaatkan momentum, tapi periksa detailnya sebelum melesat."),
    "w09": ("ketahanan, waspada, hampir sampai", "lelah, curiga berlebihan",
            "Kamu sudah melewati banyak hal dan masih bertahan; garis akhir sudah dekat.",
            "Kelelahan membuatmu curiga pada semua hal, atau ingin berhenti terlalu cepat.",
            "Istirahat sejenak, lalu selesaikan bagian terakhir."),
    "w10": ("beban berat, tanggung jawab berlebih", "melepas beban, mendelegasikan",
            "Kamu memikul terlalu banyak tanggung jawab sendirian.",
            "Saatnya melepas sebagian beban, atau beban itu mulai berkurang.",
            "Pilih apa yang benar-benar milikmu untuk dipikul; delegasikan sisanya."),
    "w11": ("antusias, ide baru, eksplorasi", "plin-plan, ide tanpa eksekusi",
            "Semangat muda untuk mencoba hal baru, atau kabar menarik yang datang.",
            "Banyak ide, tapi mudah bosan dan sulit menuntaskan.",
            "Jelajahi rasa penasaranmu, lalu pilih satu untuk ditekuni."),
    "w12": ("aksi, petualangan, berani", "impulsif, mudah marah, tak sabar",
            "Energi untuk bergerak cepat dan berani mengejar tujuan.",
            "Tindakan impulsif atau emosi yang panas bisa merusak rencana.",
            "Bergeraklah dengan berani, tapi tetap pegang kendali."),
    "w13": ("percaya diri, hangat, karismatik", "cemburu, tidak aman, menuntut",
            "Kehangatan dan rasa percaya dirimu menarik dan menginspirasi orang lain.",
            "Rasa tidak aman muncul sebagai cemburu atau keinginan mengontrol.",
            "Tampil apa adanya; kehangatanmu adalah kekuatan."),
    "w14": ("visioner, pemimpin, teladan", "otoriter, ekspektasi berlebihan",
            "Kepemimpinan dengan visi yang jelas; kamu mampu mengarahkan dan memberi teladan.",
            "Gaya memimpin terlalu keras, atau menuntut hal yang tidak realistis.",
            "Pimpin dengan visi, bukan dengan tekanan."),
    # ── Cawan / Cups ─────────────────────────────────────────────────────────
    "c01": ("cinta baru, perasaan meluap, intuisi", "emosi terpendam, terasa hampa",
            "Awal baru dalam perasaan: cinta, persahabatan, atau rasa syukur yang meluap.",
            "Perasaan tertahan, sulit terbuka, atau sedang merasa kosong.",
            "Buka hati untuk menerima, dimulai dari mengasihi diri sendiri."),
    "c02": ("kemitraan, saling tertarik, kesepakatan", "tidak seimbang, komunikasi putus",
            "Ikatan setara antara dua pihak: romantis, persahabatan, atau kerja sama.",
            "Hubungan terasa timpang, atau ada jarak yang perlu dibicarakan.",
            "Bangun hubungan di atas rasa saling menghargai."),
    "c03": ("persahabatan, perayaan, komunitas", "berlebihan, gosip, pihak ketiga",
            "Kebersamaan dan dukungan dari teman; ada alasan untuk merayakan.",
            "Kesenangan yang berlebihan, gosip, atau pihak ketiga yang mengganggu.",
            "Luangkan waktu bersama orang-orang yang membuatmu jadi dirimu sendiri."),
    "c04": ("jenuh, apatis, merenung", "bangkit, mau menerima tawaran",
            "Kamu sedang jenuh dan mungkin tak melihat peluang yang sebenarnya sedang ditawarkan.",
            "Mulai bangkit dari kejenuhan dan siap menerima hal baru.",
            "Perhatikan apa yang sedang ditawarkan kepadamu."),
    "c05": ("kehilangan, kecewa, penyesalan", "menerima, memaafkan, pulih",
            "Kekecewaan membuatmu fokus pada yang tumpah, bukan pada yang masih tersisa.",
            "Kamu mulai menerima dan perlahan bangkit.",
            "Akui sedihnya, lalu lihat dua cawan yang masih berdiri."),
    "c06": ("nostalgia, kenangan, ketulusan", "terjebak masa lalu",
            "Kenangan manis, atau seseorang dari masa lalu, hadir kembali.",
            "Terlalu terikat pada masa lalu sehingga sulit melangkah.",
            "Ambil kehangatan masa lalu, bukan bebannya."),
    "c07": ("banyak pilihan, angan-angan, ilusi", "kejelasan, mulai fokus",
            "Banyak pilihan menggoda, tapi tidak semuanya nyata.",
            "Kabut tersingkap; kamu mulai tahu mana yang benar-benar kamu mau.",
            "Bedakan mimpi yang bisa dikerjakan dari sekadar khayalan."),
    "c08": ("meninggalkan, mencari makna", "ragu pergi, takut melepas",
            "Kamu siap meninggalkan sesuatu yang tak lagi memberi makna.",
            "Ragu pergi, padahal hati sudah tidak di sana.",
            "Berani pergi dari yang sudah tidak menumbuhkanmu."),
    "c09": ("kepuasan, harapan terkabul, syukur", "puas semu, berlebihan",
            "Kartu 'harapan terkabul': ada rasa puas dan cukup.",
            "Kepuasan yang dangkal, atau mengejar kesenangan secara berlebihan.",
            "Syukuri yang sudah ada, sambil tetap jujur pada keinginanmu."),
    "c10": ("kebahagiaan keluarga, harmoni, rumah", "keretakan, gambaran ideal yang membebani",
            "Kebahagiaan emosional yang utuh, terutama bersama keluarga atau orang tercinta.",
            "Ada keretakan, atau gambaran 'keluarga ideal' yang justru membebani.",
            "Rawat kebersamaan lewat hal-hal kecil sehari-hari."),
    "c11": ("kabar manis, kreatif, peka", "emosi labil, kekanak-kanakan",
            "Kabar manis, ajakan, atau intuisi kreatif yang muncul tak terduga.",
            "Perasaan mudah berubah, atau sulit mengungkapkan diri dengan dewasa.",
            "Dengarkan bisikan hatimu dengan rasa ingin tahu."),
    "c12": ("romantis, tawaran, idealis", "janji kosong, moody",
            "Datangnya tawaran atau pendekatan yang tulus dan penuh perasaan.",
            "Kata-kata manis yang tidak diikuti tindakan nyata.",
            "Ikuti hatimu, tapi pastikan kakimu tetap menapak tanah."),
    "c13": ("empati, intuisi, kelembutan", "terlalu larut, kurang batas",
            "Kepekaan dan kasih sayang yang dalam; kamu mampu memahami perasaan orang lain.",
            "Terlalu menyerap emosi orang lain sampai lupa pada diri sendiri.",
            "Berempati boleh, tapi tetap jaga batas dirimu."),
    "c14": ("tenang, bijak secara emosi, diplomatis", "memendam, memanipulasi",
            "Mampu tetap tenang dan bijak meski perasaan sedang bergejolak.",
            "Emosi dipendam terlalu lama, atau dipakai untuk mengendalikan orang lain.",
            "Akui perasaanmu, lalu tanggapi dengan kepala dingin."),
    # ── Pedang / Swords ──────────────────────────────────────────────────────
    "s01": ("kejernihan, kebenaran, ide tajam", "bingung, salah paham",
            "Pikiran jernih dan kebenaran yang menembus kebingungan.",
            "Pikiran kacau, atau informasi yang menyesatkan.",
            "Katakan dengan jujur dan jelas apa yang sebenarnya kamu pikirkan."),
    "s02": ("jalan buntu, dilema, menghindar", "kebenaran terungkap, harus memilih",
            "Kamu menunda keputusan sulit dengan menutup mata.",
            "Penundaan tak bisa dipertahankan lagi; informasi baru memaksamu memilih.",
            "Buka mata pada fakta, lalu ambil keputusan."),
    "s03": ("patah hati, luka, kesedihan", "pulih, memaafkan",
            "Rasa sakit hati, kekecewaan, atau kebenaran yang menyakitkan.",
            "Luka mulai sembuh dan kamu siap melepaskannya.",
            "Beri ruang untuk berduka; luka yang diakui lebih cepat pulih."),
    "s04": ("istirahat, pemulihan, jeda", "kelelahan, gelisah",
            "Saatnya beristirahat dan memulihkan pikiran sebelum melangkah lagi.",
            "Memaksakan diri terus bergerak padahal tubuh dan pikiran butuh jeda.",
            "Istirahat bukan kemunduran; jadwalkan waktu tenang."),
    "s05": ("konflik, menang tapi kalah, ego", "ingin berdamai, menyesal",
            "Konflik di mana menang pun terasa kosong karena ada yang terluka.",
            "Muncul keinginan berdamai, atau penyesalan atas pertengkaran.",
            "Tanyakan pada dirimu: lebih penting benar, atau tetap terhubung?"),
    "s06": ("transisi, meninggalkan masalah, menuju tenang", "sulit pergi, beban terbawa",
            "Kamu bergerak meninggalkan masa sulit menuju perairan yang lebih tenang.",
            "Sulit pergi, atau beban lama ikut terbawa ke tempat baru.",
            "Melangkahlah perlahan; tidak perlu sembuh dalam semalam."),
    "s07": ("strategi, diam-diam, kurang jujur", "ketahuan, ingin mengaku",
            "Ada sesuatu yang dilakukan diam-diam, oleh orang lain atau oleh dirimu sendiri.",
            "Rahasia terbuka, atau muncul dorongan untuk berterus terang.",
            "Tetap waspada, dan pastikan caramu sendiri tetap jujur."),
    "s08": ("terjebak, membatasi diri, tak berdaya", "terlepas, sudut pandang baru",
            "Merasa terkurung, padahal sebagian ikatannya ada di dalam pikiran sendiri.",
            "Kamu mulai melihat jalan keluar.",
            "Uji keyakinan yang membatasimu; satu langkah kecil bisa membebaskan."),
    "s09": ("cemas, overthinking, sulit tidur", "kecemasan mereda, mencari bantuan",
            "Kecemasan dan pikiran yang berputar membuat masalah terasa lebih besar dari aslinya.",
            "Ketakutan mulai mereda, atau kamu mulai mencari bantuan.",
            "Ceritakan pada orang yang kamu percaya; jangan ditanggung sendirian."),
    "s10": ("titik terendah, akhir yang menyakitkan", "bangkit, pulih",
            "Sebuah babak berakhir dengan cara yang menyakitkan. Ini titik terendah, bukan selamanya.",
            "Masa terburuk sudah lewat dan pemulihan dimulai.",
            "Terima akhirnya; fajar selalu datang setelah malam paling gelap."),
    "s11": ("ingin tahu, waspada, ide baru", "gosip, bicara tanpa pikir",
            "Rasa ingin tahu yang tajam; saatnya belajar, bertanya, dan mengamati.",
            "Kata-kata tajam tanpa pertimbangan, atau terlalu curiga.",
            "Ajukan pertanyaan yang tepat sebelum mengambil kesimpulan."),
    "s12": ("tegas, ambisius, cepat bertindak", "gegabah, kasar",
            "Bergerak cepat dan tegas mengejar tujuan dengan logika.",
            "Terlalu terburu-buru sampai melukai orang lain dengan kata-kata.",
            "Kecepatan itu bagus, tapi pikirkan dampaknya."),
    "s13": ("mandiri, jujur, berpikiran jernih", "dingin, getir",
            "Penilaian yang jernih, kejujuran, dan batas yang tegas.",
            "Pengalaman pahit membuat sikap terlalu dingin atau sinis.",
            "Bersikap jujur dan tegas, tetap dengan hati."),
    "s14": ("otoritas, adil, logis", "manipulatif, kaku",
            "Keputusan diambil berdasarkan logika, etika, dan kebenaran.",
            "Kecerdasan dipakai untuk mengontrol, atau sikap terlalu kaku.",
            "Gunakan logika untuk keadilan, bukan untuk menang sendiri."),
    # ── Koin / Pentacles ─────────────────────────────────────────────────────
    "p01": ("peluang baru, kemakmuran, awal yang nyata", "peluang terlewat, kurang rencana",
            "Peluang nyata dalam pekerjaan, keuangan, atau kesehatan sedang terbuka.",
            "Peluang terlewat, atau rencananya belum cukup matang.",
            "Tanam benih yang konkret: tabungan, keterampilan, atau kebiasaan baik."),
    "p02": ("menyeimbangkan, beradaptasi, prioritas", "kewalahan, berantakan",
            "Kamu menyeimbangkan beberapa urusan sekaligus dengan luwes.",
            "Terlalu banyak yang dipegang hingga mulai kewalahan.",
            "Tentukan prioritas; tidak semua harus dipegang bersamaan."),
    "p03": ("kerja tim, keahlian, kolaborasi", "kurang kerja sama, hasil asal-asalan",
            "Kerja sama dan keahlian menghasilkan sesuatu yang berkualitas.",
            "Tim tidak sejalan, atau usaha belum maksimal.",
            "Hargai peran masing-masing dan kerjakan bagianmu dengan sungguh-sungguh."),
    "p04": ("menyimpan, rasa aman, kontrol", "terlalu menggenggam, belajar melepas",
            "Menjaga apa yang dimiliki demi rasa aman.",
            "Terlalu menggenggam sampai menghambat, atau mulai belajar melepas.",
            "Rasa aman itu penting, tapi jangan sampai genggamanmu menutup aliran baru."),
    "p05": ("kesulitan, kekurangan, merasa ditinggal", "pulih, bantuan datang",
            "Masa sulit secara materi atau merasa terasing; padahal bantuan sebenarnya dekat.",
            "Kesulitan mulai berlalu dan dukungan mulai datang.",
            "Jangan malu meminta bantuan; pintu yang terang ada di dekatmu."),
    "p06": ("memberi dan menerima, kedermawanan", "utang budi, timpang",
            "Pertukaran yang adil: memberi, menerima, atau berbagi rezeki.",
            "Bantuan dengan syarat tersembunyi, atau hubungan yang timpang.",
            "Berbagilah dengan tulus dan terima bantuan tanpa malu."),
    "p07": ("kesabaran, investasi jangka panjang, evaluasi", "tidak sabar, hasil kurang",
            "Saatnya menilai hasil kerja; panen butuh waktu.",
            "Frustrasi karena hasil lambat, atau usaha belum tepat sasaran.",
            "Evaluasi strategimu, lalu sabar menunggu tumbuhnya."),
    "p08": ("tekun, belajar, mengasah keahlian", "perfeksionis, kurang fokus",
            "Ketekunan mengasah keterampilan sedikit demi sedikit.",
            "Pekerjaan terasa monoton, atau terjebak perfeksionisme.",
            "Latihan kecil yang konsisten mengalahkan semangat sesaat."),
    "p09": ("mandiri, nyaman, menikmati hasil", "boros, terlalu bergantung",
            "Kemandirian dan kenyamanan dari hasil kerja kerasmu sendiri.",
            "Terlalu bergantung pada orang lain, atau boros untuk hal yang tak penting.",
            "Nikmati hasil jerih payahmu dengan bijak."),
    "p10": ("warisan, stabilitas jangka panjang, keluarga", "masalah keuangan keluarga",
            "Keamanan jangka panjang, warisan, dan fondasi untuk keluarga.",
            "Ada masalah keuangan keluarga, atau tradisi yang terasa membatasi.",
            "Bangun sesuatu yang bertahan lebih lama dari dirimu."),
    "p11": ("belajar, peluang, ambisi", "menunda, kurang fokus",
            "Kesempatan belajar atau peluang baru yang bisa jadi nyata jika ditekuni.",
            "Rencananya bagus, tapi tidak juga dikerjakan.",
            "Mulailah belajar hal yang bisa memperbaiki hidupmu."),
    "p12": ("rajin, konsisten, dapat diandalkan", "jalan di tempat, membosankan",
            "Kerja keras yang stabil, rutin, dan bisa diandalkan.",
            "Terlalu berhati-hati sampai jalan di tempat.",
            "Konsisten itu kekuatan; jalan pelan pun tetap sampai."),
    "p13": ("mengasuh, praktis, membumi", "kewalahan mengurus, lupa diri",
            "Kemampuan mengurus orang lain sambil tetap realistis dan membumi.",
            "Terlalu sibuk mengurus semua hal sampai lupa merawat diri.",
            "Rawat dirimu sebaik kamu merawat orang lain."),
    "p14": ("makmur, aman, pemimpin yang membumi", "materialistis, keras kepala",
            "Keberhasilan materi, kestabilan, dan kepemimpinan yang membumi.",
            "Terlalu fokus pada uang atau status sampai menjadi kaku.",
            "Gunakan kemakmuran untuk membangun, bukan sekadar memiliki."),
}

KATEGORI = {
    "umum": "Umum",
    "cinta": "Cinta & Hubungan",
    "karier": "Karier & Studi",
    "keuangan": "Keuangan",
    "diri": "Diri & Batin",
}

KONTEKS = {
    "major": {
        "umum": "Sebagai Major Arcana, kartu ini menandai tema besar, bukan sekadar urusan sesaat.",
        "cinta": "Sebagai Major Arcana, kartu ini menunjukkan pelajaran penting dalam caramu mencintai dan dicintai.",
        "karier": "Sebagai Major Arcana, kartu ini menandakan titik penting dalam arah karier atau studimu.",
        "keuangan": "Sebagai Major Arcana, kartu ini menyorot pola besar dalam hubunganmu dengan uang dan rasa aman.",
        "diri": "Sebagai Major Arcana, kartu ini adalah cermin dari tahap pertumbuhan batinmu saat ini.",
    },
    "w": {
        "umum": "Energi api: dorongan untuk bertindak dan mencipta.",
        "cinta": "Dalam hubungan, Tongkat bicara soal gairah, ketertarikan, dan siapa yang mengambil inisiatif.",
        "karier": "Untuk karier, ini energi ambisi, proyek baru, dan keberanian mengambil peran.",
        "keuangan": "Soal uang, Tongkat menyorot usaha aktif dan peluang yang lahir dari inisiatif sendiri.",
        "diri": "Untuk diri sendiri, ini tentang menyalakan kembali semangat dan tujuan hidup.",
    },
    "c": {
        "umum": "Energi air: perasaan, kedekatan, dan suara hati.",
        "cinta": "Cawan adalah ranah asli hubungan: perasaan, kedekatan, dan kejujuran emosi.",
        "karier": "Dalam pekerjaan, Cawan menyorot suasana tim, kepuasan batin, dan apakah kerjamu terasa bermakna.",
        "keuangan": "Soal uang, Cawan mengingatkan bahwa keputusan finansial sering dipengaruhi emosi.",
        "diri": "Untuk diri sendiri, ini undangan untuk jujur pada apa yang kamu rasakan.",
    },
    "s": {
        "umum": "Energi udara: pikiran, kata-kata, dan keputusan.",
        "cinta": "Dalam hubungan, Pedang menyorot komunikasi, salah paham, dan keputusan sulit.",
        "karier": "Untuk karier, Pedang bicara soal strategi, negosiasi, dan ketajaman berpikir.",
        "keuangan": "Soal uang, Pedang mengajak berhitung dengan jernih dan tidak memutuskan saat cemas.",
        "diri": "Untuk diri sendiri, perhatikan pola pikir dan cerita yang terus kamu ulang di kepala.",
    },
    "p": {
        "umum": "Energi tanah: hal-hal nyata, tubuh, dan hasil kerja.",
        "cinta": "Dalam hubungan, Koin bicara soal komitmen nyata, kestabilan, dan kehadiran sehari-hari.",
        "karier": "Untuk karier, Koin adalah ranah aslinya: keterampilan, hasil kerja, dan pertumbuhan jangka panjang.",
        "keuangan": "Soal uang, Koin adalah suit yang paling relevan: pendapatan, tabungan, dan rencana jangka panjang.",
        "diri": "Untuk diri sendiri, Koin mengingatkan pada tubuh, rutinitas, dan hal-hal yang membumi.",
    },
}

PETUNJUK_KOSONG = {
    "w": "semangat dan inisiatif mungkin perlu dinyalakan kembali",
    "c": "sisi perasaan belum banyak diberi ruang",
    "s": "ada kebutuhan untuk berpikir lebih jernih yang belum disadari",
    "p": "hal-hal praktis dan nyata belum menjadi perhatian",
}

KOMBINASI = {
    frozenset({"m16", "m17"}): "Menara dan Bintang muncul bersamaan: setelah guncangan, pemulihan sudah menunggu.",
    frozenset({"m13", "m00"}): "Transformasi dan Si Pengelana: satu pintu tertutup, pintu lain langsung terbuka.",
    frozenset({"m18", "m19"}): "Bulan dan Matahari: kebingungan saat ini akan berganti dengan kejelasan.",
    frozenset({"m06", "c02"}): "Sepasang Kekasih dan Dua Cawan: ikatan yang kuat dan saling memilih.",
    frozenset({"m15", "m06"}): "Belenggu dan Sepasang Kekasih: periksa apakah ini cinta atau keterikatan.",
    frozenset({"m10", "m21"}): "Roda Nasib dan Dunia: satu siklus besar selesai, siklus baru berputar.",
    frozenset({"s03", "c05"}): "Tiga Pedang dan Lima Cawan: ada duka yang perlu diakui, bukan disembunyikan.",
    frozenset({"m09", "m02"}): "Sang Pertapa dan Pendeta Agung: jawabannya ditemukan dalam keheningan, bukan keramaian.",
    frozenset({"p10", "c10"}): "Sepuluh Koin dan Sepuluh Cawan: kebahagiaan yang utuh, lahir dan batin.",
    frozenset({"m01", "w01"}): "Sang Penyihir dan As Tongkat: ide yang kuat dan kemampuan untuk mewujudkannya.",
}

PERTANYAAN_REFLEKSI = {
    "major": "Pelajaran besar apa yang sedang dicoba diajarkan situasi ini kepadamu?",
    "w": "Apa satu langkah berani yang bisa kamu ambil minggu ini?",
    "c": "Apa yang sebenarnya kamu rasakan, tanpa disaring?",
    "s": "Pikiran mana yang fakta, dan mana yang hanya ketakutan?",
    "p": "Hal kecil dan konkret apa yang bisa kamu kerjakan besok?",
}


def semua_id() -> list[str]:
    ids = [f"m{i:02d}" for i in range(22)]
    for s in "wcsp":
        ids += [f"{s}{n:02d}" for n in range(1, 15)]
    return ids


ID_KARTU = semua_id()


def info_kartu(cid: str) -> dict:
    kw_t, kw_r, tegak, terbalik, saran = MAKNA[cid]
    kode, angka = cid[0], int(cid[1:])
    if kode == "m":
        inggris, indo = MAJOR[angka]
        romawi = romawi_dari(angka) if angka else "0"
        return dict(
            id=cid, major=True, suit=None, angka=angka, inggris=inggris, nama=indo,
            label=f"{romawi} · {indo}", golongan="Major Arcana", warna=WARNA_MAJOR,
            kw_tegak=kw_t, kw_terbalik=kw_r, tegak=tegak, terbalik=terbalik, saran=saran,
        )
    s = SUIT[kode]
    pk_id, pk_en = PERINGKAT[angka]
    return dict(
        id=cid, major=False, suit=kode, angka=angka,
        inggris=f"{pk_en} of {s['inggris']}", nama=f"{pk_id} {s['nama']}",
        label=f"{pk_id} {s['nama']}", golongan=f"Minor Arcana · {s['nama']}", warna=s["warna"],
        kw_tegak=kw_t, kw_terbalik=kw_r, tegak=tegak, terbalik=terbalik, saran=saran,
    )


def romawi_dari(n: int) -> str:
    angka = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    hasil = ""
    for nilai, simbol in angka:
        while n >= nilai:
            hasil += simbol
            n -= nilai
    return hasil


# ─────────────────────────────────────────────────────────────────────────────
# Spread (tata letak)
# ─────────────────────────────────────────────────────────────────────────────

SPREAD = {
    "satu": {
        "nama": "Satu Kartu", "ringkas": "Pesan inti — cepat dan fokus", "layout": "row", "lebar": 230,
        "posisi": [("Pesan Utama", "inti jawaban atas pertanyaanmu", "inti")],
    },
    "tiga_waktu": {
        "nama": "Lalu · Kini · Nanti", "ringkas": "Tiga kartu untuk melihat alur waktu", "layout": "row", "lebar": 180,
        "posisi": [
            ("Masa Lalu", "akar yang membentuk situasi ini", "lalu"),
            ("Masa Kini", "energi yang sedang berlangsung", "kini"),
            ("Masa Depan", "arah yang mungkin bila semuanya berjalan seperti sekarang", "hasil"),
        ],
    },
    "tiga_saran": {
        "nama": "Situasi · Hambatan · Saran", "ringkas": "Tiga kartu yang langsung memberi arah", "layout": "row", "lebar": 180,
        "posisi": [
            ("Situasi", "gambaran keadaanmu saat ini", "kini"),
            ("Hambatan", "apa yang menahan atau menantangmu", "hambatan"),
            ("Saran", "langkah yang dianjurkan kartu", "saran"),
        ],
    },
    "pilihan": {
        "nama": "Dua Jalan", "ringkas": "Lima kartu untuk menimbang dua pilihan", "layout": "pilihan", "lebar": 140,
        "posisi": [
            ("Dirimu Saat Ini", "posisi dan sikapmu menghadapi pilihan ini", "kini"),
            ("Jalan A", "energi pilihan pertama", "a"),
            ("Hasil Jalan A", "ke mana pilihan pertama cenderung membawamu", "hasil"),
            ("Jalan B", "energi pilihan kedua", "b"),
            ("Hasil Jalan B", "ke mana pilihan kedua cenderung membawamu", "hasil"),
        ],
    },
    "hubungan": {
        "nama": "Hubungan", "ringkas": "Lima kartu untuk dinamika dua pihak", "layout": "row", "lebar": 140,
        "posisi": [
            ("Kamu", "perasaan dan peranmu dalam hubungan ini", "kini"),
            ("Pihak Lain", "perasaan dan peran orang tersebut", "lain"),
            ("Ikatan Saat Ini", "kondisi hubungan kalian sekarang", "inti"),
            ("Tantangan", "yang perlu diperhatikan atau diperbaiki", "hambatan"),
            ("Arah ke Depan", "ke mana hubungan ini cenderung bergerak", "hasil"),
        ],
    },
    "keltik": {
        "nama": "Salib Keltik", "ringkas": "Sepuluh kartu, pembacaan paling mendalam", "layout": "keltik", "lebar": 104,
        "posisi": [
            ("Situasi Inti", "inti keadaan saat ini", "inti"),
            ("Tantangan", "hal yang menyilang atau menghalangi", "hambatan"),
            ("Akar", "dasar atau penyebab yang lebih dalam", "lalu"),
            ("Masa Lalu", "yang baru saja berlalu", "lalu"),
            ("Harapan Sadar", "tujuan atau yang sedang kamu pikirkan", "tujuan"),
            ("Masa Dekat", "yang akan segera datang", "dekat"),
            ("Dirimu", "sikap dan posisimu", "kini"),
            ("Lingkungan", "pengaruh orang dan keadaan di sekitarmu", "lain"),
            ("Harapan & Ketakutan", "yang diam-diam kamu harapkan atau takuti", "batin"),
            ("Hasil yang Mungkin", "arah akhir bila jalur saat ini dipertahankan", "hasil"),
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Gambar
# ─────────────────────────────────────────────────────────────────────────────


def _bintang(cx: float, cy: float, r1: float, r2: float, ujung: int = 8) -> str:
    titik = []
    for i in range(ujung * 2):
        r = r1 if i % 2 == 0 else r2
        sudut = math.pi * i / ujung - math.pi / 2
        titik.append(f"{cx + r * math.cos(sudut):.1f},{cy + r * math.sin(sudut):.1f}")
    return " ".join(titik)


def svg_punggung() -> str:
    sinar = "".join(
        f'<line x1="{175 + 76 * math.cos(a):.1f}" y1="{300 + 76 * math.sin(a):.1f}" '
        f'x2="{175 + 90 * math.cos(a):.1f}" y2="{300 + 90 * math.sin(a):.1f}"/>'
        for a in [i * math.pi / 12 for i in range(24)]
    )
    sudut = "".join(
        f'<polygon points="{_bintang(x, y, 9, 3.5, 4)}" fill="#d6b46a"/>'
        for x, y in [(52, 52), (298, 52), (52, 548), (298, 548)]
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 350 600">
<defs>
<radialGradient id="g" cx="50%" cy="46%" r="72%"><stop offset="0" stop-color="#3b2559"/><stop offset=".55" stop-color="#1e1333"/><stop offset="1" stop-color="#0e0919"/></radialGradient>
<pattern id="t" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="13" cy="13" r="1.1" fill="#d6b46a" opacity=".32"/></pattern>
<mask id="bulanA"><rect width="350" height="600" fill="#fff"/><circle cx="183" cy="138" r="17" fill="#000"/></mask>
<mask id="bulanB"><rect width="350" height="600" fill="#fff"/><circle cx="167" cy="462" r="17" fill="#000"/></mask>
</defs>
<rect width="350" height="600" rx="20" fill="#0b0714"/>
<rect x="9" y="9" width="332" height="582" rx="15" fill="url(#g)"/>
<rect x="9" y="9" width="332" height="582" rx="15" fill="url(#t)"/>
<rect x="22" y="22" width="306" height="556" rx="10" fill="none" stroke="#d6b46a" stroke-width="2"/>
<rect x="30" y="30" width="290" height="540" rx="6" fill="none" stroke="#d6b46a" stroke-width=".8" opacity=".55"/>
{sudut}
<g fill="none" stroke="#d6b46a">
<circle cx="175" cy="300" r="112" stroke-width=".8" opacity=".45"/>
<circle cx="175" cy="300" r="98" stroke-width="1.4" opacity=".75"/>
<circle cx="175" cy="300" r="70" stroke-width="2"/>
<g stroke-width="1.6" opacity=".85">{sinar}</g>
</g>
<polygon points="{_bintang(175, 300, 56, 22, 8)}" fill="#d6b46a" opacity=".92"/>
<polygon points="{_bintang(175, 300, 30, 12, 8)}" fill="#1e1333"/>
<circle cx="175" cy="300" r="7" fill="#f0d896"/>
<circle cx="175" cy="140" r="18" fill="#d6b46a" mask="url(#bulanA)"/>
<circle cx="175" cy="460" r="18" fill="#d6b46a" mask="url(#bulanB)"/>
<line x1="175" y1="168" x2="175" y2="192" stroke="#d6b46a" stroke-width="1.2" opacity=".6"/>
<line x1="175" y1="408" x2="175" y2="432" stroke="#d6b46a" stroke-width="1.2" opacity=".6"/>
</svg>"""


@st.cache_data(show_spinner=False)
def uri_punggung() -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg_punggung().encode()).decode()


def path_kartu(cid: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = CARD_DIR / f"{cid}{ext}"
        if p.exists():
            return p
    return None


def svg_cadangan(cid: str) -> str:
    k = info_kartu(cid)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 350 600">
<rect width="350" height="600" rx="18" fill="#efe4c8"/>
<rect x="16" y="16" width="318" height="568" rx="10" fill="none" stroke="#5a4320" stroke-width="3"/>
<text x="175" y="290" text-anchor="middle" font-family="Georgia,serif" font-size="30" fill="#3a2a12">{html.escape(k['nama'])}</text>
<text x="175" y="330" text-anchor="middle" font-family="Georgia,serif" font-size="18" fill="#6b5530">{html.escape(k['inggris'])}</text>
</svg>"""


@st.cache_data(show_spinner=False)
def uri_kartu(cid: str) -> str:
    p = path_kartu(cid)
    if p is None:
        return "data:image/svg+xml;base64," + base64.b64encode(svg_cadangan(cid).encode()).decode()
    mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp"}[p.suffix.lower()]
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


# ─────────────────────────────────────────────────────────────────────────────
# Logika pembacaan
# ─────────────────────────────────────────────────────────────────────────────

POLA_TERTUTUP = re.compile(
    r"^\s*(apakah|apa\s+(dia|ia|aku\s+akan)|akankah|kapan|benarkah|siapa|berapa)\b", re.IGNORECASE
)


def cek_pertanyaan(teks: str) -> str | None:
    if teks.strip() and POLA_TERTUTUP.search(teks):
        return (
            "Pertanyaanmu tertutup (ya/tidak atau menebak waktu). Tarot lebih tajam untuk pertanyaan "
            "terbuka, misalnya: <b>“Apa yang perlu aku pahami tentang …?”</b> atau "
            "<b>“Bagaimana aku bisa …?”</b>"
        )
    return None


def waktu_sekarang() -> datetime:
    return datetime.now(ZONA_WAKTU)


def format_tanggal(dt: datetime, jam: bool = True) -> str:
    teks = f"{HARI[dt.weekday()]}, {dt.day} {BULAN[dt.month - 1]} {dt.year}"
    return f"{teks} · {dt:%H.%M} WIB" if jam else teks


def kocok(dek: list[str]) -> list[str]:
    rng = random.SystemRandom()
    dek = dek[:]
    for _ in range(3):  # tiga kali riffle + acak penuh
        tengah = len(dek) // 2 + rng.randint(-4, 4)
        kiri, kanan, hasil = dek[:tengah], dek[tengah:], []
        while kiri or kanan:
            sumber = kiri if (kiri and (not kanan or rng.random() < len(kiri) / (len(kiri) + len(kanan)))) else kanan
            hasil.append(sumber.pop(0))
        dek = hasil
    rng.shuffle(dek)
    return dek


def potong(dek: list[str], tumpukan: int) -> list[str]:
    n = len(dek)
    a, b = n // 3, 2 * n // 3
    bagian = [dek[:a], dek[a:b], dek[b:]]
    pilih = bagian.pop(tumpukan)
    return pilih + bagian[0] + bagian[1]


def tarik(dek: list[str], jumlah: int, terbalik_aktif: bool) -> list[dict]:
    rng = random.SystemRandom()
    return [
        {"id": cid, "terbalik": terbalik_aktif and rng.random() < PELUANG_TERBALIK}
        for cid in dek[:jumlah]
    ]


def analisis(kartu: list[dict]) -> dict:
    infos = [info_kartu(k["id"]) for k in kartu]
    suit = Counter(i["suit"] for i in infos if not i["major"])
    angka = Counter(i["angka"] for i in infos if not i["major"] and i["angka"] <= 10)
    return {
        "n": len(kartu),
        "major": sum(i["major"] for i in infos),
        "suit": suit,
        "terbalik": sum(k["terbalik"] for k in kartu),
        "angka": angka,
        "court": [i for i in infos if not i["major"] and i["angka"] >= 11],
        "ids": {k["id"] for k in kartu},
    }


def suit_dominan(a: dict) -> str | None:
    if not a["suit"]:
        return None
    (s1, n1), *sisa = a["suit"].most_common()
    if n1 >= 2 and (not sisa or sisa[0][1] < n1):
        return s1
    return None


def benang_merah(bacaan: dict) -> list[str]:
    kartu, kat = bacaan["kartu"], bacaan["kategori"]
    a = analisis(kartu)
    n, p = a["n"], []

    if n == 1:
        k = info_kartu(kartu[0]["id"])
        kunci = "major" if k["major"] else k["suit"]
        p.append(KONTEKS[kunci][kat])
    else:
        if a["major"] / n >= 0.5:
            p.append(
                f"Lebih dari separuh kartumu ({a['major']} dari {n}) adalah Major Arcana. Situasi ini "
                "menyentuh tema hidup yang besar — sesuatu yang sedang membentukmu, bukan sekadar urusan sesaat."
            )
        elif a["major"] == 0:
            p.append(
                "Tidak ada Major Arcana yang muncul. Situasi ini lebih banyak berada di ranah sehari-hari, "
                "artinya sebagian besar masih ada dalam kendalimu."
            )
        else:
            p.append(
                f"Ada {a['major']} Major Arcana di antara {n} kartu: satu-dua tema besar bekerja di latar, "
                "tetapi banyak hal tetap bisa kamu atur sendiri."
            )

        dom = suit_dominan(a)
        if dom:
            s = SUIT[dom]
            p.append(
                f"Suit <b>{s['nama']}</b> (elemen {s['elemen']}) paling menonjol, jadi energi bacaan ini "
                f"berpusat pada {s['ranah']}. {KONTEKS[dom][kat]}"
            )
        elif n >= 3 and sum(a["suit"].values()) >= 2:
            p.append(
                "Tidak ada suit yang benar-benar mendominasi: situasi ini menyentuh beberapa sisi hidupmu sekaligus, "
                "jadi jawabannya kemungkinan perlu keseimbangan, bukan satu langkah tunggal."
            )
        if n >= 5:
            kosong = [s for s in "wcsp" if a["suit"][s] == 0]
            if kosong and len(kosong) <= 2:
                bagian = "; ".join(f"tidak ada {SUIT[s]['nama']} — {PETUNJUK_KOSONG[s]}" for s in kosong)
                p.append(bagian[0].upper() + bagian[1:] + ".")

        if bacaan["terbalik_aktif"]:
            if a["terbalik"] / n >= 0.5:
                p.append(
                    "Banyak kartu keluar terbalik. Energinya ada, tetapi tertahan, tertunda, atau sedang diproses "
                    "di dalam. Ini sering menjadi tanda untuk melambat dan membereskan dari dalam dulu."
                )
            elif a["terbalik"] == 0 and n >= 3:
                p.append("Semua kartu keluar tegak: energinya mengalir terbuka dan cukup jelas terbaca.")

        for angka_, jml in a["angka"].items():
            if jml >= 2:
                p.append(f"Angka {angka_} muncul {jml} kali, menguatkan tema <i>{MAKNA_ANGKA[angka_]}</i>.")

        if len(a["court"]) >= 2:
            p.append(
                f"Ada {len(a['court'])} kartu court (Page, Ksatria, Ratu, Raja). Kemungkinan beberapa orang ikut "
                "berperan dalam situasi ini, atau kamu sedang memainkan beberapa peran sekaligus."
            )

        for pasangan, teks in KOMBINASI.items():
            if pasangan <= a["ids"]:
                p.append(teks)

    return p


def inti_pesan(bacaan: dict) -> str:
    posisi = SPREAD[bacaan["spread"]]["posisi"]
    peran = [ps[2] for ps in posisi]
    for target in ("saran", "inti", "hasil"):
        if target in peran:
            k = bacaan["kartu"][peran.index(target)]
            return info_kartu(k["id"])["saran"]
    return info_kartu(bacaan["kartu"][-1]["id"])["saran"]


def refleksi(bacaan: dict) -> list[str]:
    a = analisis(bacaan["kartu"])
    urutan: list[str] = []
    dom = suit_dominan(a)
    if a["major"] and a["major"] >= max(a["suit"].values(), default=0):
        urutan.append("major")
    if dom:
        urutan.append(dom)
    for k in bacaan["kartu"]:
        i = info_kartu(k["id"])
        urutan.append("major" if i["major"] else i["suit"])
    hasil, sudah = [], set()
    for kunci in urutan:
        if kunci not in sudah:
            sudah.add(kunci)
            hasil.append(PERTANYAAN_REFLEKSI[kunci])
        if len(hasil) == 3:
            break
    if a["terbalik"]:
        hasil.append("Bagian mana dari dirimu yang sedang menahan diri, dan apa yang ia lindungi?")
    return hasil[:3]


def ke_markdown(bacaan: dict) -> str:
    sp = SPREAD[bacaan["spread"]]
    baris = [
        "# Arcana — Hasil Bacaan Tarot",
        "",
        f"**Waktu:** {bacaan['waktu_teks']}  ",
        f"**Pertanyaan:** {bacaan['pertanyaan']}  ",
        f"**Fokus:** {KATEGORI[bacaan['kategori']]}  ",
        f"**Tata letak:** {sp['nama']}",
        "",
        "## Kartu per posisi",
        "",
    ]
    for (nama, desk, _), k in zip(sp["posisi"], bacaan["kartu"]):
        i = info_kartu(k["id"])
        arah = "terbalik" if k["terbalik"] else "tegak"
        makna = i["terbalik"] if k["terbalik"] else i["tegak"]
        kw = i["kw_terbalik"] if k["terbalik"] else i["kw_tegak"]
        baris += [
            f"### {nama} — {i['nama']} ({i['inggris']}), {arah}",
            f"*{desk[0].upper() + desk[1:]}.*",
            "",
            f"Kata kunci: {kw}.  ",
            f"{makna}",
            "",
        ]
    baris += ["## Benang merah", ""]
    baris += [re.sub(r"</?[bi]>", "", t) for t in benang_merah(bacaan)]
    baris += ["", "## Inti pesan", "", f"> {inti_pesan(bacaan)}", "", "## Untuk direnungkan", ""]
    baris += [f"- {q}" for q in refleksi(bacaan)]
    baris += [
        "",
        "---",
        "*Tarot adalah alat refleksi, bukan ramalan pasti. Keputusan penting tetap ada di tanganmu.*",
    ]
    return "\n".join(baris)


# ─────────────────────────────────────────────────────────────────────────────
# Tampilan: CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root{
  --bg:#0b0814; --bg2:#141024; --panel:rgba(30,22,48,.66); --panel2:rgba(42,31,66,.55);
  --gold:#d6b46a; --gold2:#f1d99a; --ink:#efe6d2; --muted:#a69cb7; --line:rgba(214,180,106,.22);
  --rose:#d98a9c; --cw:160px;
}
html, body, .stApp{ background:var(--bg); }
.stApp{
  color:var(--ink);
  font-family:'Plus Jakarta Sans', system-ui, sans-serif;
  background:
    radial-gradient(1px 1px at 12% 18%, rgba(255,240,210,.55) 50%, transparent 51%),
    radial-gradient(1px 1px at 72% 12%, rgba(255,240,210,.45) 50%, transparent 51%),
    radial-gradient(1.4px 1.4px at 88% 64%, rgba(255,240,210,.5) 50%, transparent 51%),
    radial-gradient(1px 1px at 34% 78%, rgba(255,240,210,.4) 50%, transparent 51%),
    radial-gradient(1.2px 1.2px at 56% 42%, rgba(255,240,210,.35) 50%, transparent 51%),
    radial-gradient(1px 1px at 6% 62%, rgba(255,240,210,.45) 50%, transparent 51%),
    radial-gradient(900px 600px at 85% -10%, rgba(120,72,170,.28), transparent 60%),
    radial-gradient(800px 600px at -10% 30%, rgba(214,180,106,.10), transparent 60%),
    radial-gradient(1000px 700px at 50% 120%, rgba(78,42,120,.35), transparent 60%),
    var(--bg);
  background-attachment: fixed;
}
[data-testid="stHeader"]{ background:transparent; }
.block-container{ max-width:1180px; padding-top:2.2rem; padding-bottom:5rem; }
h1,h2,h3,h4{ font-family:'Cormorant Garamond', Georgia, serif !important; color:var(--ink); letter-spacing:.01em; }
p, li, label, .stMarkdown{ color:var(--ink); }
[data-testid="stCaptionContainer"], .stCaption{ color:var(--muted) !important; }

/* Tab */
.stTabs [data-baseweb="tab-list"]{ gap:6px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"]{
  font-family:'Cinzel', serif; font-size:.82rem; letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); padding:10px 16px; border-radius:10px 10px 0 0; background:transparent;
}
.stTabs [aria-selected="true"]{ color:var(--gold2) !important; background:linear-gradient(180deg, rgba(214,180,106,.12), transparent); }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--gold) !important; }
.stTabs [data-baseweb="tab-border"]{ display:none; }

/* Tombol */
.stButton > button, .stDownloadButton > button{
  border-radius:999px; border:1px solid var(--line); background:var(--panel2); color:var(--ink);
  font-weight:600; letter-spacing:.02em; padding:.55rem 1.3rem; transition:all .2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--gold); color:var(--gold2); transform:translateY(-1px); }
.stButton > button[kind="primary"]{
  background:linear-gradient(135deg, #e6c67e, #b98f45); color:#1a1206; border:none;
  box-shadow:0 8px 28px -10px rgba(214,180,106,.65);
}
.stButton > button[kind="primary"]:hover{ color:#1a1206; filter:brightness(1.07); }
.stButton > button:disabled{ opacity:.45; }

/* Input */
.stTextArea textarea, .stTextInput input{
  background:rgba(20,15,34,.85) !important; border:1px solid var(--line) !important; color:var(--ink) !important;
  border-radius:14px !important; font-size:1rem;
}
.stTextArea textarea:focus, .stTextInput input:focus{ border-color:var(--gold) !important; box-shadow:0 0 0 1px var(--gold) !important; }
[data-testid="stWidgetLabel"] p{ color:var(--gold2); font-weight:600; letter-spacing:.02em; }
[data-baseweb="select"] > div{ background:rgba(20,15,34,.85); border-color:var(--line); border-radius:12px; }

/* Radio sebagai kartu pilihan */
div[role="radiogroup"]{ gap:10px; }
div[role="radiogroup"] > label{
  background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:12px 14px; margin:0;
  transition:border-color .2s;
}
div[role="radiogroup"] > label:has(input:checked){ border-color:var(--gold); background:rgba(214,180,106,.09); }

/* Komponen umum */
.hero{ text-align:center; padding:8px 0 22px; }
.hero .eyebrow{ font-family:'Cinzel',serif; letter-spacing:.42em; font-size:.72rem; color:var(--gold); }
.hero h1{ font-family:'Cinzel',serif !important; font-size:clamp(2.6rem,6vw,4.2rem); margin:.15em 0 .05em; letter-spacing:.14em;
  background:linear-gradient(180deg,#fff3d4,#d6b46a 70%,#a07a36); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero p{ color:var(--muted); font-family:'Cormorant Garamond',serif; font-size:1.3rem; font-style:italic; margin:0; }
.hero .rule{ width:180px; height:1px; margin:16px auto 0; background:linear-gradient(90deg,transparent,var(--gold),transparent); position:relative; }
.hero .rule:after{ content:"✦"; position:absolute; left:50%; top:50%; transform:translate(-50%,-55%); color:var(--gold); background:var(--bg); padding:0 10px; font-size:.8rem; }

.panel{ background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:22px 24px; backdrop-filter:blur(6px); }
.judul-bagian{ font-family:'Cinzel',serif; letter-spacing:.24em; text-transform:uppercase; font-size:.78rem; color:var(--gold); margin:30px 0 12px; display:flex; align-items:center; gap:12px; }
.judul-bagian:after{ content:""; flex:1; height:1px; background:linear-gradient(90deg,var(--line),transparent); }
.tip{ border-left:3px solid var(--gold); background:rgba(214,180,106,.08); padding:12px 16px; border-radius:0 12px 12px 0; color:var(--ink); font-size:.95rem; line-height:1.55; }
.tip.peringatan{ border-color:var(--rose); background:rgba(217,138,156,.09); }
.chip{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:.75rem; font-weight:600; letter-spacing:.03em; border:1px solid var(--line); color:var(--muted); margin:0 6px 6px 0; }
.chip.tegak{ color:#b8e0b0; border-color:rgba(184,224,176,.35); }
.chip.terbalik{ color:var(--rose); border-color:rgba(217,138,156,.4); }

/* Stepper */
.stepper{ display:flex; justify-content:center; gap:0; margin:6px 0 26px; flex-wrap:wrap; }
.step{ display:flex; align-items:center; gap:10px; color:var(--muted); font-size:.85rem; font-weight:600; }
.step .dot{ width:30px; height:30px; border-radius:50%; display:grid; place-items:center; border:1px solid var(--line); font-family:'Cinzel',serif; font-size:.8rem; }
.step.aktif{ color:var(--gold2); } .step.aktif .dot{ background:linear-gradient(135deg,#e6c67e,#b98f45); color:#1a1206; border:none; box-shadow:0 0 0 5px rgba(214,180,106,.15); }
.step.selesai .dot{ border-color:var(--gold); color:var(--gold); }
.step .garis{ width:46px; height:1px; background:var(--line); margin:0 10px; }

/* Dek & kocok */
.meja{ display:flex; flex-direction:column; align-items:center; padding:20px 0 6px; }
.dek{ position:relative; width:150px; height:257px; margin:10px auto 18px; }
.dek img{ position:absolute; inset:0; width:100%; height:100%; border-radius:12px; box-shadow:0 14px 34px -12px rgba(0,0,0,.8); }
.dek img:nth-child(1){ transform:translate(-6px,6px) rotate(-3deg); } .dek img:nth-child(2){ transform:translate(-3px,3px) rotate(-1.5deg); }
.dek img:nth-child(4){ transform:translate(3px,-3px) rotate(1.5deg); } .dek img:nth-child(5){ transform:translate(6px,-6px) rotate(3deg); }
.dek.kocok img:nth-child(odd){ animation:kiri .9s ease-in-out 2; } .dek.kocok img:nth-child(even){ animation:kanan .9s ease-in-out 2; }
@keyframes kiri{ 0%,100%{ } 40%{ transform:translateX(-92px) rotate(-10deg); } 60%{ transform:translateX(-80px) rotate(-8deg); z-index:9; } }
@keyframes kanan{ 0%,100%{ } 40%{ transform:translateX(92px) rotate(10deg); } 60%{ transform:translateX(80px) rotate(8deg); } }
.meja .ket{ font-family:'Cormorant Garamond',serif; font-size:1.25rem; font-style:italic; color:var(--muted); text-align:center; }
.meja .hitung{ font-family:'Cinzel',serif; letter-spacing:.2em; font-size:.75rem; color:var(--gold); margin-top:6px; }
.tumpukan{ position:relative; width:118px; height:202px; margin:8px auto 12px; transition:transform .25s; }
.tumpukan img{ position:absolute; inset:0; width:100%; height:100%; border-radius:10px; box-shadow:0 10px 24px -10px #000; }
.tumpukan img:nth-child(1){ transform:translate(-4px,4px); } .tumpukan img:nth-child(3){ transform:translate(4px,-4px); }
.tumpukan:hover{ transform:translateY(-6px); }
.label-tumpukan{ text-align:center; font-family:'Cinzel',serif; letter-spacing:.2em; font-size:.75rem; color:var(--gold); }

/* Spread */
.kepala-bacaan{ text-align:center; margin:6px 0 4px; }
.kepala-bacaan .q{ font-family:'Cormorant Garamond',serif; font-size:clamp(1.5rem,3.2vw,2.1rem); font-style:italic; line-height:1.25; color:var(--ink); }
.kepala-bacaan .meta{ color:var(--muted); font-size:.85rem; margin-top:8px; }
.spread{ display:flex; flex-wrap:wrap; justify-content:center; align-items:flex-start; gap:30px 24px; padding:28px 6px 10px; }
.slot{ width:var(--cw); display:flex; flex-direction:column; align-items:center; position:relative; }
/* Kartu: sisi muka selalu tampil secara default. Animasi balik dibuat dua tahap
   (punggung memutar 0→90°, lalu muka -90→0°) sehingga tidak bergantung pada
   preserve-3d/backface-visibility yang sering diratakan di dalam halaman Streamlit. */
.kartu3d{ width:var(--cw); aspect-ratio:350/600; position:relative; }
.inner{ position:relative; width:100%; height:100%; }
.face{ position:absolute; inset:0; border-radius:12px; overflow:hidden;
  box-shadow:0 18px 40px -16px rgba(0,0,0,.9), 0 0 0 1px rgba(214,180,106,.25); }
.face img{ width:100%; height:100%; object-fit:cover; display:block; }
.front{ background:#efe4c8; opacity:1; }
.back{ opacity:0; visibility:hidden; }
.inner.anim .back{ animation:tutup 1.5s ease-in-out var(--d,0s) both; }
.inner.anim .front{ animation:buka 1.5s ease-out var(--d,0s) both; }
@keyframes tutup{
  0%{ opacity:0; visibility:visible; transform:perspective(900px) translateY(-26px) rotateY(0deg); }
  15%{ opacity:1; visibility:visible; }
  55%{ opacity:1; visibility:visible; transform:perspective(900px) translateY(-8px) rotateY(0deg); }
  77%{ opacity:1; visibility:visible; transform:perspective(900px) translateY(-4px) rotateY(90deg); }
  78%, 100%{ opacity:0; visibility:hidden; transform:perspective(900px) rotateY(90deg); }
}
@keyframes buka{
  0%, 77%{ opacity:0; transform:perspective(900px) translateY(-4px) rotateY(-90deg); }
  78%{ opacity:1; transform:perspective(900px) translateY(-4px) rotateY(-90deg); }
  100%{ opacity:1; transform:perspective(900px) translateY(0) rotateY(0deg); }
}
@media (prefers-reduced-motion: reduce){ .inner.anim .back, .inner.anim .front{ animation:none; } }
.front img.rev{ transform:rotate(180deg); }
.slot:hover .face.front{ box-shadow:0 22px 50px -14px rgba(214,180,106,.45), 0 0 0 1px var(--gold); }
.cap{ margin-top:12px; font-family:'Cinzel',serif; letter-spacing:.14em; font-size:.66rem; text-transform:uppercase; color:var(--gold); text-align:center; line-height:1.4; }
.cap .no{ display:inline-grid; place-items:center; width:18px; height:18px; border-radius:50%; border:1px solid var(--gold); margin-right:5px; font-size:.6rem; }
.cname{ font-family:'Cormorant Garamond',serif; font-size:1.08rem; font-weight:600; text-align:center; line-height:1.2; margin-top:3px; }
.cname .rv{ display:block; font-family:'Plus Jakarta Sans',sans-serif; font-size:.7rem; font-weight:600; color:var(--rose); letter-spacing:.06em; margin-top:2px; }

.spread.pilihan{ display:grid; grid-template-columns:repeat(3,var(--cw)); grid-template-areas:"p3 . p5" "p2 . p4" ". p1 ."; justify-content:center; column-gap:34px; }
.spread.keltik{ display:grid; grid-template-columns:repeat(3,var(--cw)) var(--cw); grid-template-areas:". p5 . p10" "p4 p1 p6 p9" ". p3 . p8" ". . . p7";
  justify-content:center; column-gap:calc(var(--cw)*.5); row-gap:20px; }
.spread.keltik .slot.staf{ margin-left:calc(var(--cw)*.35); }
.spread.keltik .slot.silang{ z-index:3; pointer-events:none; }
.spread.keltik .slot.silang .kartu3d{ transform:rotate(90deg); }
.spread.keltik .slot.silang .cap, .spread.keltik .slot.silang .cname{ display:none; }
.badge-silang{ display:none; }
.spread.keltik .slot.silang .badge-silang{ display:grid; position:absolute; top:calc(var(--cw)*.86 - 11px); left:calc(var(--cw) + var(--cw)*.36 - 8px);
  place-items:center; width:22px; height:22px; border-radius:50%; background:var(--gold); color:#1a1206; font:700 .7rem 'Cinzel',serif; }

@media (max-width: 760px){
  .spread{ gap:22px 14px; }
  .spread .slot, .spread .kartu3d{ --cw: min(var(--cwm), 40vw) !important; }
  .spread.pilihan, .spread.keltik{ display:flex; }
  .spread.keltik .slot.staf{ margin-left:0; }
  .spread.keltik .slot.silang{ pointer-events:auto; }
  .spread.keltik .slot.silang .kartu3d{ transform:none; }
  .spread.keltik .slot.silang .cap, .spread.keltik .slot.silang .cname{ display:block; }
  .spread.keltik .slot.silang .badge-silang{ display:none; }
  .stepper .garis{ width:16px; margin:0 4px; } .stepper .lbl{ display:none; }
}

/* Energi */
.energi{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
.energi .item{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px 16px; }
.energi .nm{ font-size:.75rem; color:var(--muted); font-weight:600; letter-spacing:.06em; text-transform:uppercase; }
.energi .val{ font-family:'Cormorant Garamond',serif; font-size:1.9rem; font-weight:700; line-height:1.1; margin-top:2px; }
.energi .bar{ height:5px; background:rgba(255,255,255,.07); border-radius:3px; margin-top:8px; overflow:hidden; }
.energi .bar span{ display:block; height:100%; border-radius:3px; }

/* Tafsir per posisi */
.tafsir{ display:grid; grid-template-columns:92px 1fr; gap:20px; align-items:start; background:var(--panel); border:1px solid var(--line);
  border-radius:18px; padding:18px 20px; margin-bottom:14px; }
.tafsir img{ width:92px; border-radius:8px; box-shadow:0 10px 24px -10px #000; }
.tafsir img.rev{ transform:rotate(180deg); }
.tafsir .pos{ font-family:'Cinzel',serif; letter-spacing:.16em; text-transform:uppercase; font-size:.72rem; color:var(--gold); }
.tafsir .desk{ color:var(--muted); font-size:.85rem; font-style:italic; margin:2px 0 8px; }
.tafsir h4{ margin:0 0 8px !important; font-size:1.45rem !important; padding:0 !important; }
.tafsir h4 small{ font-family:'Plus Jakarta Sans',sans-serif; font-size:.8rem; color:var(--muted); font-weight:500; margin-left:6px; }
.tafsir p{ margin:6px 0 0; line-height:1.65; }
.tafsir .konteks{ color:var(--muted); font-size:.9rem; margin-top:8px; }
@media (max-width: 560px){ .tafsir{ grid-template-columns:64px 1fr; gap:14px; padding:14px; } .tafsir img{ width:64px; } }

/* Oracle / benang merah */
.oracle{ position:relative; background:linear-gradient(160deg, rgba(58,37,89,.55), rgba(20,15,34,.7)); border:1px solid var(--line);
  border-radius:22px; padding:28px 30px; }
.oracle p{ font-family:'Cormorant Garamond',serif; font-size:1.28rem; line-height:1.6; margin:0 0 12px; }
.oracle p:first-of-type::first-letter{ font-family:'Cinzel',serif; float:left; font-size:3.1rem; line-height:.9; padding:6px 10px 0 0; color:var(--gold); }
.kutipan{ text-align:center; padding:26px 18px; }
.kutipan .isi{ font-family:'Cormorant Garamond',serif; font-size:clamp(1.5rem,3vw,2rem); font-style:italic; line-height:1.35; color:var(--gold2); }
.kutipan .isi:before{ content:"“"; } .kutipan .isi:after{ content:"”"; }
.renungan li{ font-size:1.02rem; line-height:1.6; margin-bottom:6px; }
.catatan{ color:var(--muted); font-size:.82rem; text-align:center; margin-top:28px; line-height:1.6; }

/* Kartu harian */
.harian{ display:grid; grid-template-columns:minmax(200px,300px) 1fr; gap:36px; align-items:center; }
.harian .kartu3d{ --cw: 100%; width:100%; }
.harian .tgl{ font-family:'Cinzel',serif; letter-spacing:.24em; font-size:.75rem; color:var(--gold); text-transform:uppercase; }
.harian h2{ font-size:clamp(2rem,4vw,2.8rem) !important; margin:.2em 0 .1em !important; padding:0 !important; }
.harian .ing{ color:var(--muted); font-style:italic; margin-bottom:14px; }
.harian p{ font-size:1.05rem; line-height:1.7; }
@media (max-width: 720px){ .harian{ grid-template-columns:1fr; } .harian .wrap-kartu{ max-width:240px; margin:0 auto; } }

/* Ensiklopedia */
.nama-grid{ text-align:center; font-family:'Cormorant Garamond',serif; font-weight:600; font-size:1.02rem; line-height:1.2; margin:6px 0 2px; min-height:2.4em; }
[data-testid="stImage"] img{ border-radius:10px; box-shadow:0 12px 26px -12px #000; }
.detail h3{ font-size:2rem !important; margin:0 !important; padding:0 !important; }
.detail .gol{ font-family:'Cinzel',serif; letter-spacing:.18em; text-transform:uppercase; font-size:.72rem; color:var(--gold); }
.detail .blok{ margin-top:14px; }
.detail .blok b{ color:var(--gold2); }
.detail p{ line-height:1.65; margin:4px 0; }

/* Riwayat */
.mini{ display:flex; gap:6px; flex-wrap:wrap; margin:6px 0 4px; }
.mini img{ width:46px; border-radius:5px; box-shadow:0 6px 14px -6px #000; }
.mini img.rev{ transform:rotate(180deg); }

/* Panduan */
.panduan h3{ font-size:1.6rem !important; color:var(--gold2) !important; }
.panduan p, .panduan li{ line-height:1.7; font-size:1.0rem; }
.grid-suit{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:10px 0; }
.grid-suit .s{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px; }
.grid-suit .s b{ font-family:'Cormorant Garamond',serif; font-size:1.3rem; }
.grid-suit .s span{ display:block; color:var(--muted); font-size:.9rem; margin-top:4px; line-height:1.5; }

footer, #MainMenu{ visibility:hidden; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Tampilan: komponen HTML
# ─────────────────────────────────────────────────────────────────────────────


def tampil(isi: str) -> None:
    st.html(isi)


def judul(teks: str) -> None:
    tampil(f'<div class="judul-bagian">{teks}</div>')


def html_slot(no: int, posisi: tuple, kartu: dict, animasi: bool, jeda: float, kelas: str = "", lebar_hp: int = 150) -> str:
    i = info_kartu(kartu["id"])
    rev = "rev" if kartu["terbalik"] else ""
    anim = "anim" if animasi else ""
    tanda = '<span class="rv">TERBALIK</span>' if kartu["terbalik"] else ""
    return (
        f'<div class="slot p{no} {kelas}" style="grid-area:{"p1" if "silang" in kelas else f"p{no}"};--d:{jeda:.2f}s;--cwm:{lebar_hp}px">'
        f'<div class="kartu3d"><div class="inner {anim}">'
        f'<div class="face back"><img src="{uri_punggung()}" alt="Punggung kartu"/></div>'
        f'<div class="face front"><img class="{rev}" src="{uri_kartu(kartu["id"])}" alt="{html.escape(i["nama"])}"/></div>'
        f'</div></div>'
        f'<div class="badge-silang">{no}</div>'
        f'<div class="cap"><span class="no">{no}</span>{html.escape(posisi[0])}</div>'
        f'<div class="cname">{html.escape(i["nama"])}{tanda}</div>'
        f'</div>'
    )


def html_spread(bacaan: dict, animasi: bool) -> str:
    sp = SPREAD[bacaan["spread"]]
    lebar = sp["lebar"]
    slot = []
    for idx, (posisi, kartu) in enumerate(zip(sp["posisi"], bacaan["kartu"]), start=1):
        kelas = ""
        if sp["layout"] == "keltik":
            if idx == 2:
                kelas = "silang"
            elif idx >= 7:
                kelas = "staf"
        lebar_hp = 120 if len(sp["posisi"]) > 3 else (150 if len(sp["posisi"]) == 3 else 220)
        slot.append(html_slot(idx, posisi, kartu, animasi, 0.15 + 0.32 * (idx - 1), kelas, lebar_hp))
    return f'<div class="spread {sp["layout"]}" style="--cw:{lebar}px">{"".join(slot)}</div>'


def html_stepper(aktif: int) -> str:
    langkah = ["Pertanyaan", "Kocok", "Potong", "Bacaan"]
    bagian = []
    for i, nama in enumerate(langkah):
        status = "aktif" if i == aktif else ("selesai" if i < aktif else "")
        simbol = "✓" if i < aktif else str(i + 1)
        bagian.append(f'<div class="step {status}"><div class="dot">{simbol}</div><span class="lbl">{nama}</span></div>')
        if i < len(langkah) - 1:
            bagian.append('<div class="step"><div class="garis"></div></div>')
    return f'<div class="stepper">{"".join(bagian)}</div>'


def html_energi(bacaan: dict) -> str:
    a = analisis(bacaan["kartu"])
    n = a["n"]
    item = [("Major Arcana", a["major"], WARNA_MAJOR)] + [
        (f'{SUIT[s]["nama"]} · {SUIT[s]["elemen"]}', a["suit"][s], SUIT[s]["warna"]) for s in "wcsp"
    ]
    blok = "".join(
        f'<div class="item"><div class="nm">{nm}</div><div class="val" style="color:{w}">{v}</div>'
        f'<div class="bar"><span style="width:{(v / n) * 100:.0f}%;background:{w}"></span></div></div>'
        for nm, v, w in item
    )
    if bacaan["terbalik_aktif"]:
        blok += (
            f'<div class="item"><div class="nm">Terbalik</div><div class="val" style="color:var(--rose)">{a["terbalik"]}</div>'
            f'<div class="bar"><span style="width:{(a["terbalik"] / n) * 100:.0f}%;background:var(--rose)"></span></div></div>'
        )
    return f'<div class="energi">{blok}</div>'


def html_tafsir(no: int, posisi: tuple, kartu: dict, kategori: str) -> str:
    i = info_kartu(kartu["id"])
    t = kartu["terbalik"]
    kw = i["kw_terbalik"] if t else i["kw_tegak"]
    makna = i["terbalik"] if t else i["tegak"]
    chip_arah = '<span class="chip terbalik">Terbalik</span>' if t else '<span class="chip tegak">Tegak</span>'
    chips = "".join(f'<span class="chip">{html.escape(x.strip())}</span>' for x in kw.split(","))
    konteks = KONTEKS["major" if i["major"] else i["suit"]][kategori]
    return (
        f'<div class="tafsir">'
        f'<img class="{"rev" if t else ""}" src="{uri_kartu(kartu["id"])}" alt=""/>'
        f'<div><div class="pos">{no} · {html.escape(posisi[0])}</div>'
        f'<div class="desk">{html.escape(posisi[1][0].upper() + posisi[1][1:])}</div>'
        f'<h4>{html.escape(i["nama"])}<small>{html.escape(i["inggris"])}</small></h4>'
        f'<div>{chip_arah}{chips}</div>'
        f'<p>{html.escape(makna)}</p>'
        f'<div class="konteks">{html.escape(konteks)}</div>'
        f'</div></div>'
    )


def html_mini(kartu: list[dict]) -> str:
    return '<div class="mini">' + "".join(
        f'<img class="{"rev" if k["terbalik"] else ""}" src="{uri_kartu(k["id"])}" title="{html.escape(info_kartu(k["id"])["nama"])}"/>'
        for k in kartu
    ) + "</div>"


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────


def init_state() -> None:
    bawaan = {
        "langkah": 0,
        "pertanyaan": "",
        "kategori": "umum",
        "spread": "tiga_waktu",
        "terbalik_aktif": True,
        "dek": ID_KARTU[:],
        "jumlah_kocok": 0,
        "animasi_kocok": False,
        "bacaan": None,
        "animasi_buka": False,
        "riwayat": [],
    }
    for k, v in bawaan.items():
        st.session_state.setdefault(k, v)


def mulai_ulang() -> None:
    st.session_state.update(
        langkah=0, dek=ID_KARTU[:], jumlah_kocok=0, bacaan=None, animasi_buka=False, animasi_kocok=False
    )


# ─────────────────────────────────────────────────────────────────────────────
# Halaman: Baca Kartu
# ─────────────────────────────────────────────────────────────────────────────


def halaman_baca() -> None:
    langkah = st.session_state.langkah
    tampil(html_stepper(langkah))
    if langkah == 0:
        langkah_pertanyaan()
    elif langkah == 1:
        langkah_kocok()
    elif langkah == 2:
        langkah_potong()
    else:
        langkah_hasil()


def langkah_pertanyaan() -> None:
    # Widget memakai key "w_*" lalu disalin ke state permanen saat lanjut,
    # karena Streamlit menghapus state widget yang tidak dirender di langkah lain.
    ss = st.session_state
    kiri, kanan = st.columns([1.15, 1], gap="large")
    with kiri:
        judul("1 · Rumuskan pertanyaanmu")
        pertanyaan = st.text_area(
            "Apa yang ingin kamu pahami?",
            value=ss.pertanyaan,
            key="w_pertanyaan",
            placeholder="Contoh: Apa yang perlu aku pahami tentang arah karierku tahun depan?",
            height=110,
            max_chars=240,
        )
        saran = cek_pertanyaan(pertanyaan)
        if saran:
            tampil(f'<div class="tip peringatan">{saran}</div>')
        else:
            tampil(
                '<div class="tip">Tarik napas, lalu tulis satu pertanyaan yang jujur. Pertanyaan terbuka '
                '(<i>apa, bagaimana, apa yang perlu</i>) memberi jawaban yang paling berguna. '
                'Boleh dikosongkan untuk pesan umum.</div>'
            )
        st.write("")
        kategori = st.selectbox(
            "Fokus bacaan",
            options=list(KATEGORI),
            index=list(KATEGORI).index(ss.kategori),
            key="w_kategori",
            format_func=lambda k: KATEGORI[k],
        )
        terbalik = st.toggle(
            "Izinkan kartu terbalik",
            value=ss.terbalik_aktif,
            key="w_terbalik",
            help="Kartu terbalik menunjukkan energi yang tertahan, tertunda, atau sedang diproses di dalam.",
        )
    with kanan:
        judul("2 · Pilih tata letak")
        spread = st.radio(
            "Tata letak kartu",
            options=list(SPREAD),
            index=list(SPREAD).index(ss.spread),
            key="w_spread",
            format_func=lambda k: f"{SPREAD[k]['nama']}  ·  {len(SPREAD[k]['posisi'])} kartu",
            captions=[SPREAD[k]["ringkas"] for k in SPREAD],
            label_visibility="collapsed",
        )
    st.write("")
    _, tengah, _ = st.columns([1, 1.2, 1])
    with tengah:
        if st.button("Lanjut ke pengocokan  ✦", type="primary", width="stretch"):
            ss.update(
                pertanyaan=pertanyaan, kategori=kategori, terbalik_aktif=terbalik, spread=spread,
                langkah=1, dek=ID_KARTU[:], jumlah_kocok=0, animasi_kocok=False,
            )
            st.rerun()


def langkah_kocok() -> None:
    n = st.session_state.jumlah_kocok
    kelas = "kocok" if st.session_state.animasi_kocok else ""
    st.session_state.animasi_kocok = False
    pertanyaan = st.session_state.pertanyaan.strip() or "Apa yang perlu aku ketahui saat ini?"
    gambar = "".join(f'<img src="{uri_punggung()}"/>' for _ in range(5))
    status = f"Dikocok {n}×" if n else "Belum dikocok"
    tampil(
        f'<div class="meja"><div class="ket">Fokuskan pikiranmu pada pertanyaan:<br>'
        f'<span style="color:var(--ink)">“{html.escape(pertanyaan)}”</span></div>'
        f'<div class="dek {kelas}" data-n="{n}">{gambar}</div>'
        f'<div class="hitung">{status}</div></div>'
    )
    _, a, b, _ = st.columns([1, 1, 1, 1])
    with a:
        if st.button("Kocok kartu", width="stretch", type="secondary" if n else "primary"):
            st.session_state.dek = kocok(st.session_state.dek)
            st.session_state.jumlah_kocok += 1
            st.session_state.animasi_kocok = True
            st.rerun()
    with b:
        if st.button("Lanjut: potong dek", type="primary" if n else "secondary", width="stretch", disabled=n == 0):
            st.session_state.langkah = 2
            st.rerun()
    st.write("")
    _, c, _ = st.columns([2, 1, 2])
    with c:
        if st.button("← Ubah pertanyaan", width="stretch"):
            st.session_state.langkah = 0
            st.rerun()


def langkah_potong() -> None:
    tampil(
        '<div class="meja"><div class="ket">Dek sudah dikocok. Ikuti intuisimu —<br>'
        'pilih satu tumpukan untuk diletakkan paling atas.</div></div>'
    )
    tumpukan = "".join(f'<img src="{uri_punggung()}"/>' for _ in range(3))
    _, *kolom, _ = st.columns([0.6, 1, 1, 1, 0.6])
    for idx, (k, nama) in enumerate(zip(kolom, ["Kiri", "Tengah", "Kanan"])):
        with k:
            tampil(f'<div class="tumpukan">{tumpukan}</div><div class="label-tumpukan">{nama.upper()}</div>')
            if st.button(f"Pilih {nama.lower()}", key=f"potong_{idx}", width="stretch"):
                buka_kartu(idx)
    st.write("")
    _, c, _ = st.columns([2, 1, 2])
    with c:
        if st.button("← Kocok lagi", width="stretch"):
            st.session_state.langkah = 1
            st.rerun()


def buka_kartu(tumpukan: int) -> None:
    ss = st.session_state
    dek = potong(ss.dek, tumpukan)
    sp = SPREAD[ss.spread]
    waktu = waktu_sekarang()
    bacaan = {
        "id": uuid.uuid4().hex[:8],
        "waktu": waktu.isoformat(),
        "waktu_teks": format_tanggal(waktu),
        "pertanyaan": ss.pertanyaan.strip() or "Apa yang perlu aku ketahui saat ini?",
        "kategori": ss.kategori,
        "spread": ss.spread,
        "terbalik_aktif": ss.terbalik_aktif,
        "kartu": tarik(dek, len(sp["posisi"]), ss.terbalik_aktif),
    }
    ss.bacaan = bacaan
    ss.riwayat.insert(0, bacaan)
    ss.langkah = 3
    ss.animasi_buka = True
    st.rerun()


def tampil_hasil(bacaan: dict, animasi: bool) -> None:
    sp = SPREAD[bacaan["spread"]]
    tampil(
        f'<div class="kepala-bacaan"><div class="q">“{html.escape(bacaan["pertanyaan"])}”</div>'
        f'<div class="meta">{html.escape(sp["nama"])} · {KATEGORI[bacaan["kategori"]]} · {bacaan["waktu_teks"]}</div></div>'
    )
    tampil(html_spread(bacaan, animasi))

    judul("Gambaran energi")
    tampil(html_energi(bacaan))

    judul("Tafsir per posisi")
    tampil("".join(
        html_tafsir(i, ps, k, bacaan["kategori"])
        for i, (ps, k) in enumerate(zip(sp["posisi"], bacaan["kartu"]), start=1)
    ))

    judul("Benang merah")
    paragraf = "".join(f"<p>{t}</p>" for t in benang_merah(bacaan))
    tampil(f'<div class="oracle">{paragraf}</div>')

    tampil(f'<div class="kutipan"><div class="judul-bagian" style="justify-content:center">Inti pesan</div>'
           f'<div class="isi">{html.escape(inti_pesan(bacaan))}</div></div>')

    judul("Untuk direnungkan")
    tampil('<div class="panel renungan"><ul>' + "".join(f"<li>{html.escape(q)}</li>" for q in refleksi(bacaan)) + "</ul></div>")

    tampil(
        '<div class="catatan">Tarot adalah alat refleksi, bukan ramalan pasti. Untuk urusan kesehatan, hukum, '
        'atau keuangan besar, tetap minta pendapat profesional.<br>Keputusan akhir selalu ada di tanganmu.</div>'
    )


def langkah_hasil() -> None:
    ss = st.session_state
    bacaan = ss.bacaan
    if not bacaan:
        mulai_ulang()
        st.rerun()
    animasi = ss.animasi_buka
    ss.animasi_buka = False
    tampil_hasil(bacaan, animasi)
    st.write("")
    _, a, b, _ = st.columns([1, 1.1, 1.1, 1])
    with a:
        st.download_button(
            "Unduh hasil (.md)",
            data=ke_markdown(bacaan),
            file_name=f"bacaan-tarot-{bacaan['id']}.md",
            mime="text/markdown",
            width="stretch",
        )
    with b:
        if st.button("Baca lagi  ✦", type="primary", width="stretch"):
            mulai_ulang()
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Halaman: Kartu Harian
# ─────────────────────────────────────────────────────────────────────────────


def kartu_harian(nama: str, tanggal: str) -> dict:
    benih = int(hashlib.sha256(f"{nama.strip().lower()}|{tanggal}".encode()).hexdigest(), 16)
    rng = random.Random(benih)
    return {"id": rng.choice(ID_KARTU), "terbalik": rng.random() < 0.25}


def halaman_harian() -> None:
    sekarang = waktu_sekarang()
    tanggal = sekarang.strftime("%Y-%m-%d")
    _, tengah, _ = st.columns([1, 1.6, 1])
    with tengah:
        nama = st.text_input(
            "Nama panggilanmu (opsional)",
            key="nama_harian",
            placeholder="Kartu harianmu tetap sama sepanjang hari ini",
        )
    kartu = kartu_harian(nama, tanggal)
    i = info_kartu(kartu["id"])
    t = kartu["terbalik"]
    kw = i["kw_terbalik"] if t else i["kw_tegak"]
    chips = "".join(f'<span class="chip">{html.escape(x.strip())}</span>' for x in kw.split(","))
    arah = '<span class="chip terbalik">Terbalik</span>' if t else '<span class="chip tegak">Tegak</span>'
    sapaan = f"untuk {html.escape(nama.strip())}" if nama.strip() else "untukmu"
    tampil(
        f'<div class="panel" style="margin-top:14px"><div class="harian">'
        f'<div class="wrap-kartu"><div class="kartu3d"><div class="inner anim" style="--d:.2s">'
        f'<div class="face back"><img src="{uri_punggung()}"/></div>'
        f'<div class="face front"><img class="{"rev" if t else ""}" src="{uri_kartu(kartu["id"])}"/></div>'
        f'</div></div></div>'
        f'<div><div class="tgl">Kartu hari ini {sapaan} · {format_tanggal(sekarang, jam=False)}</div>'
        f'<h2>{html.escape(i["nama"])}</h2><div class="ing">{html.escape(i["inggris"])} · {html.escape(i["golongan"])}</div>'
        f'<div>{arah}{chips}</div>'
        f'<p>{html.escape(i["terbalik"] if t else i["tegak"])}</p>'
        f'<div class="tip" style="margin-top:14px"><b>Niat hari ini:</b> {html.escape(i["saran"])}</div>'
        f'</div></div></div>'
    )
    tampil(
        '<div class="catatan">Satu kartu untuk satu hari. Kartu ini ditentukan oleh nama dan tanggal, '
        'jadi akan tetap sama sampai besok. Bacalah lagi malam ini dan lihat apa yang terasa benar.</div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Halaman: Ensiklopedia
# ─────────────────────────────────────────────────────────────────────────────


@st.dialog("Detail Kartu", width="large")
def dialog_kartu(cid: str) -> None:
    i = info_kartu(cid)
    kiri, kanan = st.columns([1, 1.6], gap="large")
    with kiri:
        p = path_kartu(cid)
        if p:
            st.image(str(p), width="stretch")
        else:
            tampil(f'<img src="{uri_kartu(cid)}" style="width:100%;border-radius:10px"/>')
    with kanan:
        if i["major"]:
            unsur = "Major Arcana — tema besar dan pelajaran hidup."
        else:
            s = SUIT[i["suit"]]
            unsur = (
                f"Elemen <b>{s['elemen']}</b> — ranah {s['ranah']}. "
                f"Angka/peringkat: <i>{MAKNA_ANGKA[i['angka']]}</i>."
            )
        tampil(
            f'<div class="detail"><div class="gol">{html.escape(i["golongan"])}</div>'
            f'<h3>{html.escape(i["nama"])}</h3><div style="color:var(--muted);font-style:italic">{html.escape(i["inggris"])}</div>'
            f'<div class="blok"><p>{unsur}</p></div>'
            f'<div class="blok"><span class="chip tegak">Tegak</span> <b>{html.escape(i["kw_tegak"])}</b><p>{html.escape(i["tegak"])}</p></div>'
            f'<div class="blok"><span class="chip terbalik">Terbalik</span> <b>{html.escape(i["kw_terbalik"])}</b><p>{html.escape(i["terbalik"])}</p></div>'
            f'<div class="blok tip"><b>Saran:</b> {html.escape(i["saran"])}</div>'
            f'</div>'
        )
        kunci = "major" if i["major"] else i["suit"]
        with st.expander("Makna menurut fokus bacaan"):
            for k, nm in KATEGORI.items():
                st.markdown(f"**{nm}** — {KONTEKS[kunci][k]}")


def halaman_ensiklopedia() -> None:
    kiri, kanan = st.columns([2, 1])
    with kiri:
        filter_ = st.segmented_control(
            "Golongan",
            options=["semua", "m", "w", "c", "s", "p"],
            format_func=lambda k: {"semua": "Semua", "m": "Major Arcana"}.get(k, SUIT.get(k, {}).get("nama", k)),
            default="semua",
            key="filter_ensiklopedia",
        ) or "semua"
    with kanan:
        cari = st.text_input("Cari kartu atau kata kunci", placeholder="mis. cinta, Ratu, awal baru", key="cari_kartu")

    q = cari.strip().lower()
    hasil = []
    for cid in ID_KARTU:
        if filter_ != "semua" and cid[0] != filter_:
            continue
        i = info_kartu(cid)
        teks = " ".join([i["nama"], i["inggris"], i["kw_tegak"], i["kw_terbalik"], i["tegak"]]).lower()
        if q and q not in teks:
            continue
        hasil.append(cid)

    st.caption(f"{len(hasil)} kartu")
    if not hasil:
        tampil('<div class="tip">Tidak ada kartu yang cocok. Coba kata kunci lain.</div>')
        return
    per_baris = 6
    for awal in range(0, len(hasil), per_baris):
        kolom = st.columns(per_baris)
        for k, cid in zip(kolom, hasil[awal:awal + per_baris]):
            with k:
                p = path_kartu(cid)
                if p:
                    st.image(str(p), width="stretch")
                else:
                    tampil(f'<img src="{uri_kartu(cid)}" style="width:100%;border-radius:10px"/>')
                tampil(f'<div class="nama-grid">{html.escape(info_kartu(cid)["nama"])}</div>')
                if st.button("Lihat makna", key=f"lihat_{cid}", width="stretch"):
                    dialog_kartu(cid)


# ─────────────────────────────────────────────────────────────────────────────
# Halaman: Riwayat
# ─────────────────────────────────────────────────────────────────────────────


def halaman_riwayat() -> None:
    riwayat = st.session_state.riwayat
    if not riwayat:
        tampil(
            '<div class="panel" style="text-align:center;padding:40px">'
            '<div style="font-family:Cormorant Garamond,serif;font-size:1.5rem;font-style:italic">Belum ada bacaan.</div>'
            '<div style="color:var(--muted);margin-top:6px">Bacaan yang kamu lakukan di sesi ini akan muncul di sini.</div></div>'
        )
        return
    st.caption(
        f"{len(riwayat)} bacaan di sesi ini. Riwayat hilang jika halaman dimuat ulang — unduh yang ingin kamu simpan."
    )
    for b in riwayat:
        sp = SPREAD[b["spread"]]
        with st.expander(f"✦  {b['pertanyaan']}  —  {sp['nama']} · {b['waktu_teks']}"):
            tampil(html_mini(b["kartu"]))
            tampil(f'<div class="kutipan" style="padding:10px"><div class="isi" style="font-size:1.3rem">{html.escape(inti_pesan(b))}</div></div>')
            a, c = st.columns(2)
            with a:
                if st.button("Buka bacaan ini", key=f"buka_{b['id']}", width="stretch"):
                    st.session_state.update(bacaan=b, langkah=3, animasi_buka=True)
                    st.rerun()
            with c:
                st.download_button(
                    "Unduh (.md)", data=ke_markdown(b), file_name=f"bacaan-tarot-{b['id']}.md",
                    mime="text/markdown", key=f"unduh_{b['id']}", width="stretch",
                )
    if st.button("Hapus semua riwayat"):
        st.session_state.riwayat = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Halaman: Panduan
# ─────────────────────────────────────────────────────────────────────────────


def halaman_panduan() -> None:
    suit = "".join(
        f'<div class="s" style="border-top:3px solid {s["warna"]}"><b>{s["nama"]}</b> '
        f'<span style="display:inline;color:var(--muted)">({s["inggris"]} · {s["elemen"]})</span>'
        f'<span>{s["ranah"][0].upper() + s["ranah"][1:]}.</span></div>'
        for s in SUIT.values()
    )
    tampil(f"""
<div class="panduan">
<div class="panel">
<h3>Apa itu tarot?</h3>
<p>Tarot adalah sistem 78 kartu bergambar yang dipakai untuk membingkai sebuah pertanyaan, lalu membacanya sebagai cerita.
Setiap kartu membawa simbol; setiap posisi di tata letak memberi konteks. Pembacaan yang baik bukan menebak masa depan,
melainkan membantumu melihat situasi dari sudut yang baru.</p>
</div>

<div class="judul-bagian">Struktur dek</div>
<div class="panel">
<p><b style="color:var(--gold2)">Major Arcana (22 kartu)</b> — tema besar kehidupan, sering dibaca sebagai perjalanan
Si Pengelana (The Fool) menuju Dunia (The World). Jika banyak muncul, situasimu menyentuh pelajaran penting.</p>
<p><b style="color:var(--gold2)">Minor Arcana (56 kartu)</b> — urusan sehari-hari, dibagi menjadi empat suit:</p>
<div class="grid-suit">{suit}</div>
<p><b style="color:var(--gold2)">Angka</b> punya pola: As adalah awal, Lima adalah gangguan, Sepuluh adalah akhir siklus.
<b style="color:var(--gold2)">Kartu court</b> — Page (belajar), Ksatria (bergerak), Ratu (menguasai ke dalam), Raja
(menguasai ke luar) — bisa berarti orang lain atau sikap dirimu sendiri.</p>
</div>

<div class="judul-bagian">Alur membaca</div>
<div class="panel">
<ol>
<li><b>Rumuskan pertanyaan.</b> Ganti “Apakah dia akan kembali?” dengan “Apa yang perlu aku pahami tentang hubungan ini?”.</li>
<li><b>Kocok dan potong.</b> Fokus pada pertanyaan saat mengocok, lalu potong dek dan letakkan tumpukan pilihanmu di atas.</li>
<li><b>Tarik kartu ke tata letak.</b> Setiap posisi punya arti sendiri — masa lalu, hambatan, saran, dan seterusnya.</li>
<li><b>Tafsirkan per kartu.</b> Gabungkan makna kartu, arti posisinya, dan arahnya (tegak atau terbalik).</li>
<li><b>Lihat pola.</b> Suit yang dominan, jumlah Major Arcana, angka yang berulang, banyaknya kartu terbalik.</li>
<li><b>Rangkai menjadi cerita.</b> Inilah inti keahlian membaca: satu narasi yang menjawab pertanyaan dan memberi langkah.</li>
</ol>
</div>

<div class="judul-bagian">Kartu terbalik</div>
<div class="panel"><p>Kartu terbalik bukan berarti “buruk”. Ia menunjukkan energi yang tertahan, tertunda, berlebihan, atau sedang
diproses di dalam diri. Kamu bisa mematikannya di langkah pertama jika lebih nyaman membaca kartu tegak saja.</p></div>

<div class="judul-bagian">Sikap yang sehat</div>
<div class="panel"><p>Tidak ada bukti ilmiah bahwa tarot bisa memprediksi masa depan. Kekuatannya ada pada refleksi: gambar yang
terbuka membuatmu menghubungkan simbol dengan hidupmu sendiri. Gunakan bacaan sebagai bahan berpikir, bukan vonis.
Untuk kesehatan, hukum, dan keuangan besar, tetap minta pendapat profesional.</p></div>
</div>
""")


# ─────────────────────────────────────────────────────────────────────────────
# Aplikasi
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(page_title="Arcana · Ruang Tarot", page_icon="🔮", layout="wide")
    init_state()
    tampil(CSS)
    tampil(
        '<div class="hero"><div class="eyebrow">RUANG TAROT</div><h1>ARCANA</h1>'
        '<p>Tanyakan dengan jujur, dengarkan dengan tenang.</p><div class="rule"></div></div>'
    )
    if not CARD_DIR.exists() or not any(CARD_DIR.iterdir()):
        st.warning(
            "Folder gambar kartu (assets/cards) tidak ditemukan. Aplikasi tetap berjalan dengan kartu pengganti."
        )
    tab_baca, tab_harian, tab_ensik, tab_riwayat, tab_panduan = st.tabs(
        ["Baca Kartu", "Kartu Harian", "Ensiklopedia", "Riwayat", "Panduan"]
    )
    with tab_baca:
        halaman_baca()
    with tab_harian:
        halaman_harian()
    with tab_ensik:
        halaman_ensiklopedia()
    with tab_riwayat:
        halaman_riwayat()
    with tab_panduan:
        halaman_panduan()


if __name__ == "__main__":
    main()
