from collections import defaultdict
from decimal import Decimal
import html
from itertools import groupby
import os
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.test import RequestFactory
# from weasyprint import HTML

# from weasyprint import HTML

from .models import  Category, Company,Masa, Position, Product, Rezervasyon, Döviz, Fiş, Sipariş,Kasa
from .forms import AddCategoryForm, AddCurrencyForm, AddLocationForm, AddProductForm, AddReservationForm, AddTableForm, DateRangeForm, ExcelUploadForm, FisKontrolForm, ReservationUpdateForm, TarihSecForm, UpdateCategoryForm,UpdateLocationForm, UpdateProductForm, UpdateTableForm
import pandas as pd
def import_products(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']

        # Excel dosyasını oku
        df = pd.read_excel(excel_file)

        # Her bir satırı dönerek Product objeleri oluştur
        for index, row in df.iterrows():
            product = Product(
                code=row['code'],
                name=row['name'],
                category=row['category'],  # Kategoriyi uygun şekilde ayarlayın
                price=row['price'],
                # İmage'i uygun şekilde ayarlamak için:
                # image=upload_product_image(None, row['image'])
            )
            product.save()

        return render(request, 'success.html')  # Başarı sayfasına yönlendirilebilirsiniz

    return render(request, 'import_products.html')  # Excel dosyasını yüklemek için form sayfasına yönlendir

def tum_menu(request):
    # # 1 koda göre # urunler = Product.objects.all().order_by('name')

    # # 2 ada göre 
    # # 3 kayıt sırasına göre
    # #
    # company = Company.objects.first()
    # if company.menu_siralama == False:
    #     urunler = Product.objects.all()
    # else:
    urunler = Product.objects.all()
    context = {
       'urunler': urunler,
    }
    return render(request,'menu.html',context)

def kasa_satis(request):
    ürünler = Product.objects.all().order_by('category__name')
    grouped_ürünler ={}
    for key,group in groupby(ürünler,key=lambda x: x.category.name):
        grouped_ürünler[key] = list(group)
    
    context = {
        'grouped_ürünler':grouped_ürünler,
                }
    return render(request, 'kasa_satis.html',context)
# Create your views here.
import requests
from bs4 import BeautifulSoup
def index(request):
    buton_görünümü = Company.objects.first().masa_görünümü
    # ürünler = Product.objects.all().order_by('category__name')
    masalar = Masa.objects.filter(hayali_masa=False).order_by('konum__name', 'num')
    # for m in masalar:
    #     print(m.num)
    # grouped_ürünler ={}
    grouped_masalar = {}
    sorted_masalar = sorted(masalar, key=lambda x: (x.konum.name, str(''.join(filter(str.isdigit, x.num)))))
    for key, group in groupby(sorted_masalar, key=lambda x: x.konum.name):
        grouped_masalar[key] = list(group)
    # for key,group in groupby(ürünler,key=lambda x: x.category.name):
    #     grouped_ürünler[key] = list(group)

    context = {
        # 'döviz_kurlari':döviz_kurlari,
        'buton_görünümü':buton_görünümü,
        # 'grouped_ürünler':grouped_ürünler,
        'grouped_masalar': grouped_masalar,  # Konuma göre ve numaraya göre sırala
    }
    print("buton_görünümü:", {buton_görünümü})

    return render(request, 'index.html',context)
from django.db.models import Sum, F, Value
from django.core.paginator import Paginator
from django.db.models.functions import Lower
def table_detail(request, konum, num):
    
    categories = Category.objects.all()
    ürünler = Product.objects.all().order_by('category__name')
    konum_obj = get_object_or_404(Position, name=konum)
    masa = get_object_or_404(Masa, num=num, konum=konum_obj)

    # Kullanıcının daha önce bağlanıp bağlanmadığını kontrol et
    # if 'masa_id' not in request.session:
    #     # Eğer bağlanmamışsa, kullanıcının session'ına masa ID'sini ekle
    #     request.session['masa_id'] = masa.id
    #     print('Masa numarası alındı:', masa.id)
    # else:
    #     # Eğer daha önce bağlandıysa, bir uyarı mesajı yazdırabilir veya başka bir işlem yapabilirsiniz
    #     print('Kullanıcı zaten bir masa numarasına bağlı.')

    # # Masa ID kontrolü
    # if request.session.get('masa_id') == masa.id:
    #     print('masa numarası doğru')
    # else:
    #     print('bu masaya bağlı değil')
    #     return redirect('index')

    # Rezervasyon kontrolü
    if masa.rez_durum == 1:
        messages.success(request, 'Bu Masanın Rezervasyonu Var')
        print('Rezervasyon var')

    # Siparişlerin sayfalama işlemi
    siparişler = Sipariş.objects.filter(masa_num=masa, siparis_fis_num=masa.mevcut_fis_num)
    paginator = Paginator(siparişler, 5)
    page_number = request.GET.get('page', 10)
    page_obj = paginator.get_page(page_number)

    # Siparişlerin toplam tutarını hesapla
    total_account = siparişler.aggregate(total=Sum(F('urun__price') * F('miktar')))['total'] or 0
    total_amount = siparişler.filter(siparis_durumu='odenmedi').aggregate(total=Sum(F('urun__price') * F('miktar')))['total'] or 0
    total_payment = siparişler.filter(siparis_durumu='odendi').aggregate(total=Sum(F('urun__price') * F('miktar')))['total'] or 0
    remaining_payment = total_account - total_payment

    # Ürün adetleri hesapla
    ürün_adetleri = {}
    for sipariş in siparişler:
        ürün = sipariş.urun
        ürün_adetleri[ürün] = ürün_adetleri.get(ürün, 0) + sipariş.miktar

    
    start_time = time.time()
    grouped_ürünler = {}
    for key, group in groupby(ürünler, key=lambda x: x.category.name):
        grouped_ürünler[key] = list(group)
    # Buraya test etmek istediğiniz kodu ekleyin
    # Zamanı durdur
    end_time = time.time()

    # Geçen süreyi hesapla
    elapsed_time = end_time - start_time

    # Elapsed time'ı yazdır
    print(f"Kodun çalışma süresi: {elapsed_time} saniye")
    context = {
        
        'categories': categories,
        'page_obj': page_obj,
        'grouped_ürünler': grouped_ürünler,
        'masa': masa,
        'siparişler': siparişler,
        'ürün_adetleri': ürün_adetleri,
        'total_amount': total_amount,
        'total_payment': total_payment,
        'remaining_payment': remaining_payment,
        'total_account': total_account,
    }

    return render(request, 'table_detail.html', context)
def category_product(request):
    # Kodun başladığı zamanı kaydet
    start_time = time.time()

    categories = Category.objects.all()
    context = {'categories': categories}  # Başlangıçta context'i tanımlayın
    
    if request.method == 'POST' and request.is_ajax():
        # AJAX isteğini işle
        kategori_id = request.POST.get('id')
        category = get_object_or_404(Category, id=kategori_id)
        ürünler = Product.objects.filter(category=category).order_by('category')

        # Render the product list template to a string
        product_html = render_to_string('product_list_partial.html', {'ürünler': ürünler})

        # Return the product HTML as JSON
        return JsonResponse({'html': product_html})

    # Elapsed time'ı yazdır
    end_time = time.time()  # Kodun bittiği zamanı kaydet
    elapsed_time = end_time - start_time  # Geçen süreyi hesapla

    print(f"Kodun çalışma süresi: {elapsed_time} saniye") 
    return render(request, 'deneme_urun.html', context)
    
    # Form gönderilmediyse veya GET isteği yapıldıysa, sadece sayfayı render et
    
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
from django.templatetags.static import static
import os
import uuid
os.add_dll_directory(r"C:\Program Files\GTK3-Runtime Win64\bin")
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from weasyprint import HTML
def siparis_gir(request, konum, masa_num):
    masa = get_object_or_404(Masa, konum__name=konum, num=masa_num)
    ürünler = Product.objects.all()

    if masa.durum == False:
        masa.durum = True
        fiş = Fiş.objects.create(masa=masa)
        masa.mevcut_fis_num = fiş.fis_numarasi
        masa.save()
        
    siparis_list = []  # Tüm siparişleri tutacak liste
    print('siparis_listesi',siparis_list)
    istek = request.POST.get('istek')
    if request.method == 'POST':
        for product in ürünler:
            quantity_key = f'quantity_{product.id}'
            quantity = int(request.POST.get(quantity_key, 0))
            if quantity > 0:
                try:
                    siparis = Sipariş.objects.get(
                        urun_id=product.id,
                        masa_num=masa,
                        siparis_fis_num=masa.mevcut_fis_num,
                        istek = istek
                    )
                    siparis.miktar += quantity
                except Sipariş.DoesNotExist:
                    siparis = Sipariş.objects.create(
                        urun_id=product.id,
                        masa_num=masa,
                        miktar=quantity,
                        siparis_fis_num=masa.mevcut_fis_num,
                        istek = istek
                    )

                siparis_list.append((siparis.urun, quantity))
                siparis.save()
                print(f'Sipariş ekleniyor: {siparis.urun} - Miktar: {quantity}')
        
        print(f"Sipariş listesi: {siparis_list}")

        # PDF oluştur
        html_string = render_to_string('pdf-output.html', {'masa': masa, 'siparis_list': siparis_list,'istek':istek})
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        tarih_str = timezone.now().strftime("%Y-%m-%d")

        # PDF dosyasını belirli bir konuma kaydet
        pdf_path = os.path.join('siparisler', f'{tarih_str}-{masa_num}-{uuid.uuid4()}-siparisler.pdf')

        print(pdf_path)
        print(uuid.uuid4)
        print(pdf_path)
        with open(pdf_path, 'wb') as pdf_output:
            pdf_output.write(pdf_file)
        file_path = os.path.join('C:\\Users\\Serkan\\Desktop\\cafe_project\\cafe_project', pdf_path)
        printer_name = 'XP-80C'
        file_handle = open(file_path,'rb')
        printer_handle =win32print.OpenPrinter(printer_name)
        Job_Info = win32print.StartDocPrinter(printer_handle,1,(file_path,None,'RAW'))
        win32print.StartPagePrinter(printer_handle)
        win32print.WritePrinter(printer_handle,file_handle.read())
        win32print.EndPagePrinter(printer_handle)
        win32print.EndDocPrinter(printer_handle)
        win32print.ClosePrinter(printer_handle)
        file_handle.close()
        # HTTP response ile PDF'i gönder
        with open(pdf_path, 'rb') as pdf_response:
            response = HttpResponse(pdf_response.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename="{masa_num}-{konum}-siparisler.pdf"'
            # time.sleep(3)
            # subprocess.Popen(['C:\\Program Files (x86)\\Adobe\\Acrobat Reader DC\\Reader\\AcroRd32.exe', '/A', 'page=print', file_path], shell=True)
            # file_path = pdf_path
            # os.startfile(file_path,'print')


        messages.success(request,'Sipariş Alındı')
        group_name = "kasa_grubu"
        channel_layer = get_channel_layer()
        print('channel layere geldi')
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'kasa_guncelle',
                'message': 'siparis_alindi',
            }
        )
        return redirect(request.META.get('HTTP_REFERER'))
    

    context = {
        'ürünler': ürünler,
        'masa': masa,
    }
    return render(request, 'siparis_gir.html', context)

import os
import glob

from django.conf import settings
import os
import glob
from django.http import FileResponse
import subprocess

# def get_latest_pdf_path(request):
#     folder_path = 'C:\\Users\\Serkan\\Desktop\\cafe_project\\cafe_project\\siparisler'
    

#     pdf_files = glob.glob(os.path.join(folder_path, '*.pdf'))

#     # Dosyaları en son değiştirilen tarihe göre sırala
#     pdf_files.sort(key=os.path.getmtime, reverse=True)

#     # En son oluşturulan PDF dosyasının yolunu döndür
#     if pdf_files:
#         latest_pdf_path = pdf_files[0]
#         response = FileResponse(open(latest_pdf_path, 'rb'), content_type='application/pdf')
#         response['Content-Disposition'] = f'filename="{os.path.basename(latest_pdf_path)}"'
       
#         a = subprocess.Popen(['C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat.exe', latest_pdf_path], shell=True)
#         os.startfile('test.txt','print')
#         return response
#     else:
#         return HttpResponse("Belirtilen klasörde PDF dosyası bulunamadı.")
import win32print
import win32api
def get_latest_pdf_path(folder_path):
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL,None,1)
    for printer in printers:
        print(printer[2])
    file_path = 'C:\\Users\\Serkan\\Desktop\\cafe_project\\cafe_project\\siparisler\\2023-11-15-Z05-a924e9e4-3c5a-447b-a3ff-8082cff8c11d-siparisler.pdf'
    printer_name = 'XP-80C'
    file_handle = open(file_path,'rb')
    printer_handle =win32print.OpenPrinter(printer_name)
    Job_Info = win32print.StartDocPrinter(printer_handle,1,(file_path,None,'RAW'))
    win32print.StartPagePrinter(printer_handle)
    win32print.WritePrinter(printer_handle,file_handle.read())
    win32print.EndPagePrinter(printer_handle)
    win32print.EndDocPrinter(printer_handle)
    win32print.ClosePrinter(printer_handle)
    file_handle.close()
def print_pdf(pdf_path, printer_name):
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        default_printer_info = win32print.GetPrinter(printer_handle, 2)
        printer_info = default_printer_info.copy()
        printer_info['pDevMode'].DriverData = b'RAW'

        pdf_file = open(pdf_path, 'rb')
        printer = win32print.OpenPrinter(printer_name, printer_info)
        win32print.StartDocPrinter(printer, 1, (pdf_path, None, "RAW"))
        win32print.StartPagePrinter(printer)

        pdf_data = pdf_file.read()
        win32api.WritePrinter(printer, pdf_data)

        win32print.EndPagePrinter(printer)
        win32print.EndDocPrinter(printer)
    
    except Exception as e:
        print("Exception occurred:", e)
    
    finally:
        win32print.ClosePrinter(printer_handle)
        print('Yazdırma başarılı')

# Klasör yolunu belirtin
folder_path = 'C:\\Users\\Serkan\\Desktop\\cafe_project\\cafe_project\\siparisler'

# En son oluşturulan PDF dosyasının yolunu al
# latest_pdf_path = get_latest_pdf_path(folder_path)

# Yazdırılacak yazıcıyı belirtin
printer_name = 'PDF'  # Yazıcı adını belirtin

# Eğer en son oluşturulan PDF dosyası varsa, yazdır
# if latest_pdf_path:
#     print_pdf(latest_pdf_path, printer_name)
# else:
#     print("Belirtilen klasörde PDF dosyası bulunamadı.")
from django.template.loader import render_to_string
import tempfile
def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=Expenses.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    # Django proje dizini içinde geçici bir dizin oluşturun
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir) as output:
        html_string = render_to_string('pdf-output.html', {'expenses': [], 'total': 0})
        html = HTML(string=html_string)
        result = html.write_pdf(target=output.name)

    with open(output.name, 'rb') as pdf_file:
        response.write(pdf_file.read())

    return response
from django.contrib.auth.decorators import login_required

from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from cafe_app.custom_context import custom_context  # custom_context.py'nin olduğu yolu düzenlemelisiniz
import win32ui
@login_required


def kasa_islem(request):
    masalar = Masa.objects.filter(durum=True)
    masa_hesaplar = []
    dövizler = Döviz.objects.all()
    
    for masa in masalar:
        # Siparişlerin miktarı 0 olmayanları filtrele
        siparisler = Sipariş.objects.filter(masa_num=masa, siparis_fis_num=masa.mevcut_fis_num, miktar__gt=0)
    
        # Her bir siparişin ürün fiyatı ile miktarını çarp ve toplamı al
        siparisler = siparisler.annotate(siparis_toplami=ExpressionWrapper(F('urun__price') * F('miktar'), output_field=DecimalField()))
        
        # Siparişlerin toplamını al
        total_account = siparisler.aggregate(toplam_siparis=Sum('siparis_toplami'))['toplam_siparis'] or 0

        masa_hesaplar.append({'masa': masa, 'total_account': total_account, 'siparisler': siparisler})
    
    context = {
        'masalar':masalar,
        'dövizler': dövizler,
        'masa_hesaplar': masa_hesaplar,
        'no_account_available': not masa_hesaplar,
    }
    return render(request, 'kasa_islem.html', context)
# FİŞ TUTARINA EKLEYECEK
import win32print
import win32ui

import os
def print_pdf_to_printer(request):
   pass
# def print_pdf_view(request):
#     printer_name = "Microsoft Print to PDF"
#     output_file_path = r"C:\path\to\output\output_file.pdf"
#     print_pdf(printer_name, output_file_path)
    
# return HttpResponse("Printing request received.")
def hesabi_kapat(request, masa_num, masa_konum):
    if request.method =="POST":
        print(f"masa_num: {masa_num}, masa_konum: {masa_konum}")
    
        try:
            masa = Masa.objects.get(num=masa_num, konum__name=masa_konum)
            print(f"Found Masa: {masa}")
        except Masa.DoesNotExist:
            print("Masa not found!")
            raise Http404("Masa not found")
        siparişler = Sipariş.objects.filter(masa_num=masa, siparis_fis_num=masa.mevcut_fis_num)
        odeme_durumu = request.POST.get('payment_method','')  # 'payment_method' adlı checkbox'un durumunu 
        # odeme_durumu = request.POST.get('payment_method','')
        if odeme_durumu != 'Nakit' and odeme_durumu != 'K.Kartı':
            return redirect(request.META.get('HTTP_REFERER'))
        else: 
            for siparis in siparişler:
                if siparis.miktar == 0:
                    if masa.durum == True:
                        masa.durum = False
                        masa.save()
                else:
                    siparis.siparis_durumu = 'odendi'

                    Kasa.objects.create(
                        aciklama=f'{siparis.masa_num} masasının {siparis.urun} ürünün {siparis.miktar} adeti ödendi',
                        islem_tarihi=datetime.now(),
                        fis_num=siparis.siparis_fis_num,
                        masa_num=siparis.masa_num,
                        tutar=siparis.urun.price * siparis.miktar,
                        net_tutar = siparis.urun.price * siparis.miktar,
                        ödendigi_kur = '1',
                        odeme_durumu=odeme_durumu
                    )
                    siparis.save()
            
            if masa.durum == True:
                masa.durum = False
                masa.save()

            messages.success(request, 'Tüm hesap kapatıldı. Masa kalktıysa masayı kapatınız.')
            return redirect('kasa_islem')
def masayi_kapat(request,id):
    masa = get_object_or_404(Masa, id=id)
    siparişler = Sipariş.objects.filter(masa_num=masa, siparis_fis_num=masa.mevcut_fis_num, siparis_durumu='odenmedi')

    # Her bir sipariş için kontrol et
    for siparis in siparişler:
        if siparis.miktar > siparis.odenen_miktar:
            messages.error(request, f"Sipariş '{siparis}' ödenmedi. Masa kapatılamaz.")
            break  # Bir sipariş bile ödenmediyse masa kapatma işlemi durur
        return redirect('kasa_islem')
    else:
        # Eğer hiçbir sipariş ödenmedi değilse masa kapatma işlemini gerçekleştir
        masa.durum = False
        masa.mevcut_fis_num = None
        if masa.gecici:
            masa.delete()
        masa.save()
        messages.success(request, 'Masa Kapatıldı')
        return redirect('kasa_islem')
# def miktarli_ode(request, masa_konum, masa_num, quantity):
#     masa = get_object_or_404(Masa, num=masa_num, konum__name=masa_konum)
    
#     if request.method == 'POST':
#         for ürün_id, ödeme_miktari in request.POST.items():
#             if ürün_id.startswith('quantity_'):
#                 ürün_id = ürün_id.replace('quantity_', '')
#                 siparis_fis_num = request.POST.get(f'othervalue_{ürün_id}')
#                 print('Ürün ID:', ürün_id)
#                 print('Ödeme Miktarı:', ödeme_miktari)
#                 print('Sipariş Fis Numarası:', siparis_fis_num)
                
#                 # Ödeme miktarına göre ürünleri "ödendi" olarak işaretle
#                 ürün = Sipariş.objects.get(id=ürün_id)
#                 ödenen_adet = int(ödeme_miktari)
#                 ürün.miktar -= ödenen_adet
#                 if ürün.miktar <= 0:
#                     ürün.siparis_durumu = 'odendi'
#                 ürün.save()
                
#         return HttpResponse("Ödemeler işlendi")
#     else:
#         return HttpResponse("GET isteği gönderildi, POST isteği bekleniyor.")

def siparis_ode(request, masa_konum, masa_num, siparis_id, quantity):
    try:
        siparis = Sipariş.objects.get(id=siparis_id)
    except Sipariş.DoesNotExist:
        raise Http404("Sipariş bulunamadı")

    masa = get_object_or_404(Masa, num=masa_num, konum__name=masa_konum)
    
    if request.method == 'POST':
        odeme_miktari = request.POST.get('odeme_miktari')
        print('ödeme miktarı', odeme_miktari)
        
        if odeme_miktari.isdigit():
            odeme_miktari = int(odeme_miktari)
            if odeme_miktari > 0:
                if odeme_miktari > siparis.miktar:
                    messages.error(request, "Ödeme miktarı, sipariş miktarından fazla olamaz.")
                else:
                    siparis.odenen_miktar += odeme_miktari
                    siparis.miktar -= odeme_miktari
                    siparis.save()
                    
                    if siparis.odenen_miktar >= siparis.miktar:
                        siparis.siparis_durumu = 'odendi'
                        siparis.save()
                    
                    return redirect('masa_detay', konum=siparis.masa_num.konum.name, num=siparis.masa_num.num)
    
        context = {
            'siparis': siparis,
        }
    return redirect('masa_detay',context, konum=siparis.masa_num.konum.name, num=siparis.masa_num.num,)
from django.shortcuts import render, redirect
from .forms import AddReservationForm  # Burada forms.py dosyanıza uygun yolu eklemelisiniz
from .models import Masa

from datetime import date, datetime
from django.utils import timezone
from django.contrib import messages

def rezervasyon_ekle(request):
    if request.method == 'POST':
        form = AddReservationForm(request.POST)
        if form.is_valid():
            tarih = form.cleaned_data['tarih']

            # Sadece tarihin gün bilgisini al
            tarih_gun = tarih.day

            # Şimdi tarih_gun değişkeni sadece günü içerir.

            if tarih_gun < timezone.now().day:
                # Geçmiş tarih kontrolü
                messages.error(request, 'Geçmiş bir tarih seçilemez.')
                return redirect('rezervasyon_ekle')

            rezervasyon = form.save(commit=False)
            rezervasyon.durum = 0
            rezervasyon.save()

            # Rezervasyon yapıldığında ilgili masanın rez_durumunu güncelle
            rezervasyon.masa.rez_durum = 1
            rezervasyon.masa.save()

        return redirect('index')
    else:
        form = AddReservationForm()
    today = timezone.now().date().strftime('%Y-%m-%d')
    masalar = Masa.objects.all()
    context = {
        'form': form,
        'masalar': masalar,
        'today': today,
    }
    return render(request, 'rezervasyon_ekle.html', context)
def rezervasyon_sil(request,id):
    user = request.user
    rezervasyon = get_object_or_404(Rezervasyon, id=id)
    if request.method =="POST":
        if user.is_authenticated:
            rezervasyon.durum = 2
            rezervasyon.save()
        else:
            messages.warning(request,'Bu işleme yetkiniz bulunmuyor')
    return redirect('rezervasyon_listesi')



def odemeyi_geri_al(request, siparis_id):
    siparis = get_object_or_404(Sipariş, id=siparis_id)
    
    if request.method == 'POST':
        # Ödeme işlemleri burada gerçekleştirilebilir
        # Örneğin, sipariş durumunu güncellemek
        siparis.siparis_durumu = 'odenmedi'  # Sipariş durumunu "ödendi" olarak ayarla
        siparis.save()  # Değişiklikleri kaydet
        
        return redirect('masa_detay', konum=siparis.masa_num.konum.name, num=siparis.masa_num.num)
    return redirect('masa_detay', konum=siparis.masa_num.konum.name, num=siparis.masa_num.num)
    
# def masa_ac(request, konum, masa_num):
#     masa = get_object_or_404(Masa, konum__name=konum, num=masa_num)
    
#     if masa.durum == False:  # Eğer masa kapalıysa
#         masa.durum = True
#         masa.save()
#         fiş = Fiş.objects.create(masa=masa)
#         masa.mevcut_fis_num = fiş.fis_numarasi
#         masa.save()
#         print('masa_detaydasın')
#         return redirect('masa_detay', konum=konum, num=masa_num)
#     else:  # Eğer masa açıksa
        
#             print('masa_detaydasın')
#             return redirect('masa_detay', konum=konum, num=masa_num)
    
#     print('indexe geldin')
#     return render(request, 'index.html', {'masa': masa})

    # EKLEME ALANLARI #
from django.core.files.uploadedfile import SimpleUploadedFile

def add_category(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        update_form = UpdateCategoryForm(request.POST, request.FILES)
        form = AddCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)

            category.save()
            messages.success(request, 'Kayıt Yapıldı')
        else:
            messages.error(request, form.errors)
    else:
        form = AddCategoryForm()
        update_form = UpdateCategoryForm()

    context = {
        'update_form':update_form,
        'categories':categories,
        'form': form
    }
    print(form.errors)
    return render(request, 'add_category.html', context)
def update_category(request, id):
    user = request.user
    category = get_object_or_404(Category, id=id)
    update_form = UpdateCategoryForm
    if user.is_authenticated:
        if request.method == 'POST':
            update_form = UpdateCategoryForm(request.POST, request.FILES, instance=category)
            
            if update_form.is_valid():
                update_form.save()
                messages.success(request, 'Kayıt Güncellendi')
                return redirect('kategori_ekle')
            else:
                messages.warning(request, 'Form geçerli değil. Lütfen hataları kontrol edin.')
        else:
            update_form = UpdateCategoryForm(instance=category)

        return render(request, 'add_category.html', {'update_form': update_form})
    else:
        messages.warning(request, 'Bu işleme yetkiniz bulunmuyor')
        return redirect('kategori_ekle')
def delete_category(request,id):
    user = request.user
    category = get_object_or_404(Category, id=id)
    if user.is_authenticated:
        category.delete()
    else:
       messages.warning(request,'Bu işleme yetkiniz bulunmuyor')
    return redirect('kategori_ekle')
from django.shortcuts import render, redirect
from .models import Product
from django.contrib import messages
def add_product_from_excel(request):
    form = ExcelUploadForm()

    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            
            try:
                df = pd.read_excel(excel_file)
                products_data = df.to_dict(orient='records')
                # Bu kod, bir Pandas DataFrame'i içindeki verileri sözlükler listesi olarak almak için kullanılır.

                # 'df' bir Pandas DataFrame'i temsil eder. DataFrame, tablo benzeri veri yapılarından oluşan bir veri yapısıdır.
                # DataFrame, genellikle tablo benzeri verileri işlemek için kullanılır.

                # .to_dict() bir Pandas DataFrame'i sözlük veri yapısına dönüştürmek için kullanılan bir metoddur.
                # Bu metot, DataFrame içindeki verileri farklı şekillerde düzenleme seçenekleri sunar.

                # 'orient' parametresi, sözlüklerin nasıl düzenleneceğini belirler. 'records' seçeneği, her satırı bir sözlük olarak temsil eden bir liste oluşturur.
                # Her bir sözlük, DataFrame'deki bir satırdaki sütun adı ve değerlerini içerir.

                # Örneğin:
                #   {'code': '011', 'name': 'abc', 'category': 'Tatlılar', 'price': 10},
                #   {'code': '012', 'name': 'def', 'category': 'İçecekler', 'price': 5},
                #   {'code': '013', 'name': 'ghi', 'category': 'Atıştırmalık', 'price': 8}

                # Yukarıdaki örnek, bir DataFrame'i sözlük listesine dönüştürmek için kullanılan bu yöntemin sonucunu gösterir.
                # Her bir liste öğesi, bir DataFrame satırını temsil eder. Her bir sözlük, bir satırdaki sütun adı ve değerlerini içerir
                for data in products_data:
                    # Kategori adına göre kategori örneğini al
                    category_name = data['category']
                    category_instance = Category.objects.get(name=category_name)

                    # Ürünü oluşturup kaydet
                    Product.objects.create(
                        code=data['code'],
                        name=data['name'],
                        category=category_instance,
                        price=data['price'],
                    )

                messages.success(request, 'Ürünler Excel dosyasından başarıyla aktarıldı.')
                return redirect('import_product')
            except Exception as e:
                messages.warning(request, f'Excel dosyasından veri aktarılamadı. Hata: {str(e)}')
        else:
            messages.warning(request, 'Excel dosyasından veri aktarılamadı. Formu kontrol ediniz.')

    return render(request, 'import_product.html', {'form': form})
def add_product(request):
    categories = Category.objects.all()
    form = AddProductForm
    update_form = UpdateProductForm
    urunler = Product.objects.all()
    
    if request.method == 'POST':
        form = AddProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()  # Sadece formu kaydet, resim otomatik olarak veritabanına kaydedilir.
            messages.success(request, 'Kayıt Yapıldı')
        else:
            messages.warning(request, 'Kayıt Yapılamadı Formu Kontrol Ediniz.')

    context = {
        'update_form':update_form,
        'categories': categories,
        'form': form,
        'urunler': urunler,
    }
    print(form.errors)
    return render(request, 'add_product.html', context)
from django.utils.html import strip_tags
def update_product(request, id):
    user = request.user
    product = get_object_or_404(Product, id=id)

    if user.is_authenticated:
        if request.method == 'POST':
            update_form = UpdateProductForm(request.POST, request.FILES, instance=product)
            
            if update_form.is_valid():
                update_form.save()
                messages.success(request, 'Kayıt Güncellendi')
                return redirect('ürün_ekle')
            else:
                messages.warning(request, 'Formda hatalar var. Lütfen kontrol edin.')
        else:
            update_form = UpdateProductForm(instance=product)
        
        return render(request, 'add_product.html', {'update_form': update_form, 'urun': product})
    else:
        messages.warning(request, 'Bu işleme yetkiniz bulunmuyor')
    
    return redirect('ürün_ekle')
def update_table(request, id):
    konumlar = Position.objects.all()
    masa = get_object_or_404(Masa, id=id)

    if request.method == 'POST':
        updateform = UpdateTableForm(request.POST, instance=masa)
        if updateform.is_valid():
            updateform.save()
            messages.success(request, 'Masa güncellendi')
            return redirect('masa_ekle')
        else:
            messages.error(request, 'Geçerli bir form doldurun')
    else:
        updateform = UpdateTableForm(instance=masa)

    context = {
        'konumlar': konumlar,
        'updateform': updateform,
    }
    return render(request, 'masa_ekle.html', context)
#KONUM EKLEME İŞLEMİ BAŞL.
def delete_position(request,id):
    if request.method=="POST":
        konum = get_object_or_404(Position,id=id)
        konum.delete()
        return redirect('konum_ekle')
    else:
        messages.warning(request,'Bu geçerli bir işlem değil')
        return redirect('konum_ekle')
def add_location(request):
    konumlar = Position.objects.all()
    updateform = UpdateLocationForm
    if request.method == 'POST':
        form = AddLocationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            existing_position = Position.objects.filter(name=name)
            if existing_position:
                messages.warning(request, 'Bu Konum Var')
                return redirect('konum_ekle')
            else:
                form.save()
                messages.success(request, 'Kayıt Yapıldı')
                return redirect('konum_ekle')
        else:
            messages.error(request, 'Geçerli bir form doldurun')
    else:
        form = AddLocationForm()
        updateform = UpdateLocationForm
    context = {
        'updateform':updateform,
        'konumlar': konumlar,
        'form': form,
    }
    return render(request, 'konum_ekle.html', context)

def update_position(request, id):
    konum = get_object_or_404(Position, id=id)
    updateform = UpdateLocationForm
    if request.method == 'POST':
        updateform = UpdateLocationForm(request.POST, instance=konum)
        if updateform.is_valid():
            updateform.save()
            messages.success(request, 'Konum güncellendi')
            return redirect('konum_ekle')
        else:
            messages.error(request, 'Geçerli bir form doldurun')
    else:
        updateform = UpdateLocationForm(instance=konum)

    context = {
        'updateform': updateform,
    }
    return render(request, 'konum_ekle.html', context)
def add_table(request):  # MASA EKLEME İŞLEMİ
    masalar = Masa.objects.all()
    konumlar = Position.objects.all()

    if request.method == 'POST':
        form = AddTableForm(request.POST)
        if form.is_valid():
            konum = form.cleaned_data['konum']
            num = form.cleaned_data['num']
            hayali_masa_selected = form.cleaned_data['hayali_masa']

            # Check if the hayali_masa option is selected
            hayali_masa_value = True if hayali_masa_selected else False

            existing_table = Masa.objects.filter(konum__name=konum, num=num).first()
            if existing_table:
                messages.error(request, f"'{num}' numaralı masa '{konum}' konumunda zaten var.")
                return redirect('masa_ekle')
            else:
                # Set hayali_masa field based on the condition
                form.instance.hayali_masa = hayali_masa_value
                form.save()
                messages.success(request, 'Kayıt Yapıldı')
                return redirect('masa_ekle')  # İşlem sonrası yine eklemeye yönlendir
        else:
            messages.error(request, form.errors)
    else:
        form = AddTableForm()

    context = {
        'konumlar': konumlar,
        'masalar': masalar,
        'form': form,
    }
    return render(request, 'add_table.html', context)
#
# Yeni QrCode Oluşturma
#
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
def create_and_update_qr(request, masa_id):
    masa = Masa.objects.get(id=masa_id)

    # Eski QR kodunu sil
    if masa.qrcode:
        masa.qrcode.delete()

    # Yeni QR kodunu oluştur
    url = f"http://192.168.137.1:8000/masa_detay/{masa.konum}/{masa.num}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # QR kodunu kaydet
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    image_name = f"masa_{masa.num}_qr.png"
    masa.qrcode.save(image_name, ContentFile(buffer.getvalue()), save=False)
    masa.save()
    messages.success(request,'Yeni qrcode oluşturuldu.')

    return redirect('masa_ekle')  # Masa listesi sayfasına yönlendirme
def sell(request):
    product = Product.objects.all()
    context = {
        'product':product
    }
    return render(request,'sell.html',context)
from django.utils.timezone import datetime, make_aware

def gunluk_kasa(request):
    bugun = datetime.now().date()
    secilen_tarih = bugun
    dövizler = Döviz.objects.all()
    gunluk_kasa = Kasa.objects.filter(islem_tarihi=secilen_tarih,döviz='TL')
    kasa_toplami = gunluk_kasa.filter(kasa_manuel_cikis=None,döviz='TL').aggregate(toplam=Sum('tutar'))['toplam'] or 0
    nakit_odemeler = gunluk_kasa.filter(odeme_durumu='Nakit', kasa_manuel_cikis=None,döviz='TL').aggregate(toplam=Sum('tutar'))['toplam'] or 0
    manuel_cikislar = gunluk_kasa.filter(döviz='TL').aggregate(toplam=Sum('kasa_manuel_cikis'))['toplam'] or 0
    manuel_girisler = gunluk_kasa.filter(döviz='TL').aggregate(toplam=Sum('kasa_manuel_giris'))['toplam'] or 0
    kasa_toplami -= int(manuel_cikislar)
    nakit_odemeler -= int(manuel_cikislar)
    kredi_karti_odemeler = gunluk_kasa.filter(odeme_durumu='Kredi Kartı').aggregate(toplam=Sum('tutar'))['toplam'] or 0
    döviz_türleri = gunluk_kasa.values('döviz').distinct()

    # Her bir döviz türü için toplam tutarı hesapla
    toplam_tutarlar = {}
    for döviz_türü in döviz_türleri:
        döviz_kodu = döviz_türü['döviz']
        toplam_tutar = gunluk_kasa.filter(döviz=döviz_kodu).aggregate(toplam=Sum('tutar'))['toplam'] or 0
        toplam_tutarlar[döviz_kodu] = toplam_tutar

    if request.method == "POST":
        dövizler = Döviz.objects.all()
        secilen_tarih = request.POST.get('secilen_tarih')
        secilen_tarih = datetime.strptime(secilen_tarih, '%Y-%m-%d').date()
        gunluk_kasa = Kasa.objects.filter(islem_tarihi=secilen_tarih)
        kasa_toplami = gunluk_kasa.filter(kasa_manuel_cikis=None,döviz='TL').aggregate(toplam=Sum('tutar'))['toplam'] or 0
        # kasa toplamı için manuel çıkışları toplamayacak ve dövizi TL olanları toplayacak
        manuel_cikislar = gunluk_kasa.aggregate(toplam=Sum('kasa_manuel_cikis'))['toplam'] or 0
        manuel_girisler = gunluk_kasa.filter(döviz='TL').aggregate(toplam=Sum('kasa_manuel_giris'))['toplam'] or 0
        #manuel girişlerde sadece tlyi baz al.
        # kasa_toplami -= int(manuel_cikislar)
        döviz_türleri = gunluk_kasa.values('döviz').distinct()

    # Her bir döviz türü için toplam tutarı hesapla
        toplam_tutarlar = {}
        for döviz_türü in döviz_türleri:
            döviz_kodu = döviz_türü['döviz']
            toplam_tutar = gunluk_kasa.filter(döviz=döviz_kodu,kasa_manuel_cikis=None,).aggregate(toplam=Sum('tutar'))['toplam'] or 0
            toplam_tutarlar[döviz_kodu] = toplam_tutar
        nakit_odemeler = gunluk_kasa.filter(odeme_durumu='Nakit',döviz='TL').aggregate(toplam=Sum('tutar'))['toplam'] or 0
        nakit_odemeler -= int(manuel_cikislar)
        kredi_karti_odemeler = gunluk_kasa.filter(odeme_durumu='Kredi Kartı').aggregate(toplam=Sum('tutar'))['toplam'] or 0
        # kasa_toplami -= int(manuel_cikislar)
    context = {
        'dövizler':dövizler,
        'toplam_tutarlar':toplam_tutarlar,
        'manuel_girisler':manuel_girisler,
        'manuel_cikislar': manuel_cikislar,
        'secilen_tarih': secilen_tarih,
        'kasa_toplami': kasa_toplami,
        'gunluk_kasa': gunluk_kasa,
        'nakit_odemeler': nakit_odemeler,
        'kredi_karti_odemeler': kredi_karti_odemeler,
    }

    return render(request, 'günlük_kasa.html', context)
# GÜNLÜK KASADAN MANUEL GİRİŞ ÇIKIŞ İŞLEMLERİ
def manuel_giris_cikis(request):
    if request.method == "POST":
        secilen_tarih = request.POST.get('hidden_secilen_tarih')
        selected_doviz = request.POST.get('döviz')
        if not selected_doviz or not Döviz.objects.filter(kodu=selected_doviz).exists():
            # "TL" olarak default bir değer atayabilirsiniz
            selected_doviz = "TL"
        print(selected_doviz,'Döviz')
        print(secilen_tarih)
        secilen_tarih = datetime.strptime(secilen_tarih, '%Y-%m-%d').date()
        manuel_giris = request.POST.get('giris')
        tutar = request.POST.get('tutar')
        manuel_cikis = request.POST.get('cikis')
        aciklama = request.POST.get('aciklama')
        if manuel_giris == 'on':
            Kasa.objects.create(
                aciklama=aciklama,
                masa_num='Manuel-Giriş',
                fis_num=0,
                kasa_manuel_giris=tutar,
                kasa_manuel_cikis=None,
                islem_tarihi = secilen_tarih,
                tutar=tutar,
                net_tutar=0,
                durum=0,
                döviz=selected_doviz,
                ödendigi_kur=0,
                odeme_durumu='Nakit',
            )
        if manuel_cikis == 'on':
            Kasa.objects.create(
                aciklama=aciklama,
                masa_num='Manuel-Çıkış',
                fis_num=0,
                kasa_manuel_giris=None,
                kasa_manuel_cikis=tutar,
                islem_tarihi = secilen_tarih,
                tutar=tutar,
                net_tutar=0,
                durum=0,
                döviz='TL',
                ödendigi_kur=0,
                odeme_durumu='Nakit',
            )
        return redirect('gunluk_kasa')
def toplu_siparis_ode(request):
    iskonto_tutari = Company.objects.first().iskonto_tutari
    
    if request.method == 'POST':
        payment_methods = {}
        ödendigi_kur = None  # Varsayılan değeri belirtin

        döviz_kodu = request.POST.get('döviz_kodu')
        if döviz_kodu:
            döviz = Döviz.objects.filter(kodu=döviz_kodu).first()
            tutar_döviz = döviz.tutar
            ödendigi_kur = tutar_döviz
            print('Seçilen Döviz', döviz, tutar_döviz)

        iskonto = request.POST.get('iskonto')
        if iskonto is None:
            iskonto = 0

        for key, value in request.POST.items():
            if key.startswith('adet_'):
                siparis_id = key.split('_')[1]
                adet = int(value)

                payment_method = request.POST.get(f'payment_method_{siparis_id}', '')

                payment_methods[siparis_id] = (adet, payment_method)

        for siparis_id, (adet, payment_method) in payment_methods.items():
            try:
                if adet == 0 and payment_method == '':
                    continue

                siparis = get_object_or_404(Sipariş, id=siparis_id)

                if adet < 0 and payment_method == '':
                    if abs(adet) >= siparis.odenen_miktar:
                        messages.success(request, "Ödenen Miktardan Fazla Adet iptal edilemez")
                        break
                    else:
                        siparis.odenen_miktar -= abs(adet)
                        siparis.miktar += abs(adet)
                        siparis.save()
                        print('Buraya Geldi Siparişi İptal Etti')

                if adet >= 0:
                    if adet <= siparis.miktar:
                        siparis.miktar -= adet
                        siparis.odenen_miktar += adet

                        if siparis.miktar == 0:
                            siparis.durum = 'Ödendi'

                        fis = Fiş.objects.filter(fis_numarasi=siparis.siparis_fis_num).first()
                        print(fis)

                        if fis:
                            fis.tutar = 0
                            fis.tutar = int(fis.tutar) + siparis.urun.price * adet
                            print(fis.tutar) 
                            print(siparis.urun.price)
                            fis.indirim = iskonto
                            fis.save()

                            if payment_method != '' and (payment_method == 'Nakit' or payment_method == 'K.Kartı'):
                                if iskonto <= 0:
                                    toplam_tutar = siparis.urun.price * adet
                                    if iskonto_tutari == 1:
                                        net_tutar = toplam_tutar - (int(toplam_tutar) * int(iskonto) / 100)
                                    elif iskonto_tutari == 0:
                                        net_tutar = toplam_tutar % int(iskonto)
                                    elif iskonto_tutari == 3:
                                        net_tutar = toplam_tutar
                                else:
                                    net_tutar = siparis.urun.price * adet

                                    if döviz_kodu:
                                        net_tutar = int(net_tutar) / int(tutar_döviz)
                                        print('Döviz Kodu ', net_tutar)
                                        ödendigi_kur = döviz.tutar
                                    else:
                                        net_tutar = siparis.urun.price * adet

                                if döviz_kodu:
                                    aciklama = f'{siparis.masa_num} masasının {siparis.urun} ürünün {adet} adeti {döviz_kodu} ile ödendi'
                                    döviz = döviz_kodu
                                    net_tutar = siparis.urun.price * adet / ödendigi_kur
                                    ödendigi_kur = ödendigi_kur
                                else:
                                    aciklama = f'{siparis.masa_num} masasının {siparis.urun} ürünün {adet} adeti ödendi'
                                    döviz = 'TL'
                                    ödendigi_kur = '1.00'
                                    net_tutar = int(siparis.urun.price) * int(adet)
                                    print(f'Net Tutar : ', net_tutar)

                                try:
                                    # ... (diğer kodlar)
                                    
                                    Kasa.objects.create(
                                        siparis=siparis,
                                        aciklama=aciklama,
                                        islem_tarihi=datetime.now(),
                                        fis_num=siparis.siparis_fis_num,
                                        masa_num=siparis.masa_num,
                                        tutar=net_tutar,
                                        net_tutar=net_tutar,
                                        odeme_durumu=payment_method,
                                        döviz=döviz,
                                        ödendigi_kur=ödendigi_kur
                                    )
                                    
                                    messages.success(request, f'{siparis.urun} ürünün {adet} adeti ödendi')
                                    
                                except Exception as e:
                                    messages.error(request, f'Hata oluştu: {str(e)}')
                                    print(f'exception',e)
                                    return redirect(request.META.get('HTTP_REFERER'))

                            else:
                                messages.error(request, f'Hatalı ödeme yöntemi seçildi: {payment_method}')
                                return redirect(request.META.get('HTTP_REFERER'))

                        else:
                            messages.error(request, f"Siparişin bağlı olduğu fiş bulunamadı: {siparis.siparis_fis_num}")
                    else:
                        siparis.odenen_miktar += siparis.miktar
                        siparis.miktar = 0
                        siparis.siparis_durumu = 'Ödendi'
                        messages.success(request, f'{siparis.urun} siparişinin tamamı ödendi')
                else:
                    messages.warning(request, f"{abs(adet)} adet {siparis.urun} iptal edildi")

                siparis.save()
            except Sipariş.DoesNotExist:
                messages.error(request, 'Sipariş bulunamadı')

    return redirect(request.META.get('HTTP_REFERER'))

def siparis_iptal(request, siparis_id):
    if request.method == 'POST':
        adet = int(request.POST.get('adet', 0))
        siparis = Sipariş.objects.get(id=siparis_id)

        if siparis.siparis_durumu == 'odenmedi':
            if adet >= siparis.miktar:
                siparis.siparis_durumu = 'iptal'
                siparis.miktar = 0
            else:
                siparis.miktar -= adet

            siparis.save()
            messages.success(request, 'Sipariş iptal edildi.')

    return redirect(request.META.get('HTTP_REFERER'))
# RAPOR DENEMESİ
from datetime import datetime, timedelta

def rezervasyon_rapor(request):
    rezervasyonlar = None
    form = DateRangeForm()  # Tarih aralığı formunu oluşturun
    start_date = datetime.now().date() + timedelta(weeks=1)
    end_date = start_date + timedelta(weeks=1)
    # start_date = None
    # end_date = None
    durumlar = [0, 1, 2]

    if request.method == 'POST':
        form = DateRangeForm(request.POST)  # Form verileri ile formu doldurun
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            beklemede = form.cleaned_data['beklemede']
            geldi = form.cleaned_data['geldi']
            iptal = form.cleaned_data['iptal']
            tümü = form.cleaned_data['tümü']

            durumlar = []
            if tümü:
                durumlar = [0, 1, 2]
            if beklemede:
                durumlar.append(0)
            if geldi:
                durumlar.append(1)
            if iptal:
                durumlar.append(2)

            rezervasyonlar = Rezervasyon.objects.filter(tarih__range=[start_date, end_date], durum__in=durumlar)

            if request.POST.get('pdf') == 'on':
                pdf_response = create_pdf(rezervasyonlar,start_date,end_date)
                print(rezervasyonlar)
                return pdf_response
            

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'form': form,
        'rezervasyonlar': rezervasyonlar,
    }
    return render(request, 'rezervasyon_rapor.html', context)
def kasa_rapor(request):
    kasalar = None
    toplam_tutar = 0
    nakit_toplam = 0
    kart_toplam = 0

    form = DateRangeForm()  # Tarih aralığı formunu oluşturun
    # start_date = datetime.now().date() + timedelta(weeks=1) neden böyle bişey yaptığımı anlamadım
    start_date = datetime.now().date()
    end_date = start_date + timedelta(weeks=1)

    if request.method == 'POST':
        form = DateRangeForm(request.POST)  # Form verileri ile formu doldurun
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            if request.POST.get('nakit') == 'on':
                print("Nakit checkbox seçili.")
                kasalar = Kasa.objects.filter(islem_tarihi__range=[start_date, end_date], odeme_durumu='Nakit')
                nakit_toplam = kasalar.aggregate(nakit_toplam=Sum('tutar'))['nakit_toplam'] or 0
                kart_toplam = 0
                toplam_tutar = kasalar.aggregate(toplam=Sum('tutar'))['toplam'] or 0
            elif request.POST.get('kkartı') == 'on':
                print("K.Kartı checkbox seçili.")
                kasalar = Kasa.objects.filter(islem_tarihi__range=[start_date, end_date], odeme_durumu='K.Kartı')
                kart_toplam = kasalar.aggregate(kart_toplam=Sum('tutar'))['kart_toplam'] or 0
                nakit_toplam = 0
                toplam_tutar = kasalar.aggregate(toplam=Sum('tutar'))['toplam'] or 0
            else:
                print("Hiçbir checkbox seçili değil.")
                kasalar = Kasa.objects.filter(islem_tarihi__range=[start_date, end_date])
                toplam_tutar = kasalar.aggregate(toplam=Sum('tutar'))['toplam'] or 0

            if request.POST.get('pdf') == 'on':
                pdf_response = create_pdf(kasalar, start_date, end_date)
                return pdf_response

    context = {
        'nakit_toplam': nakit_toplam,
        'kart_toplam': kart_toplam,
        'start_date': start_date,
        'end_date': end_date,
        'form': form,
        'toplam_tutar': toplam_tutar,
        'kasalar': kasalar,
    }
    return render(request, 'kasa_rapor.html', context)
def create_pdf(rezervasyonlar, start_date, end_date):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    

    data = [['Rezervasyon ID', 'Tarih', 'Durum', 'Masa']]
    for rezervasyon in rezervasyonlar:
        durum_metni = rezervasyon.get_durum_display()  # Rezervasyonun durumunu alın
        print(durum_metni)
        data.append([str(rezervasyon.num), rezervasyon.tarih.strftime('%d-%m-%Y'), durum_metni, rezervasyon.masa])
    table = Table(data)
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), (0.7, 0.7, 0.7)), ('TEXTCOLOR', (0, 0), (-1, 0), (1, 1, 1)),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
                        ('GRID', (0, 0), (-1, -1), 0.5, (0, 0, 0, 1))])

    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    pdf_response = HttpResponse(content_type='application/pdf')
    pdf_response['Content-Disposition'] = f'attachment; filename="{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}_rezervasyon_rapor.pdf"'

    return pdf_response
from django.http import HttpResponse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from io import BytesIO
from datetime import datetime

# def tarihleri_al(request, start_date=None, end_date=None):
#     # start_date=None,
#     # end_date=None
#     rezervasyonlar = []
    
#     if request.method == 'GET':
#         # start_date ve end_date parametrelerini alın
#         print(f"Başlangıç Tarihi: {start_date}")
#         print(f"Bitiş Tarihi: {end_date}")
        
#         # Rezervasyonları alın
#         rezervasyonlar = Rezervasyon.objects.filter(tarih__range=[start_date, end_date])
        
#         # PDF içeriğini oluşturun
#         buffer = BytesIO()
#         doc = SimpleDocTemplate(buffer, pagesize=letter)
#         elements = []

#         # PDF içeriğini oluşturun (örnek olarak bir tablo ekleyebilirsiniz)
#         data = [['Rezervasyon ID', 'Tarih', 'Durum']]
#         for rezervasyon in rezervasyonlar:
#             tarih_str = rezervasyon.tarih.strftime('%d.%m.%Y')  # Tarihi gün.ay.yıl formatına çevirin
#             data.append([str(rezervasyon.num), tarih_str, rezervasyon.durum])

#         table = Table(data)
#         style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), (0, 0, 0.7)), ('TEXTCOLOR', (0, 0), (-1, 0), (1, 1, 1)),
#                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#                             ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
#                             ('GRID', (0, 0), (-1, -1), 0.5, (0, 0, 0, 1))])

#         table.setStyle(style)
#         elements.append(table)

#         # PDF dokümanını oluşturun ve yanıt olarak gönderin
#         doc.build(elements)
#         pdf = buffer.getvalue()
#         buffer.close()

#         response = HttpResponse(content_type='application/pdf')
#         response['Content-Disposition'] = f'attachment; filename="rezervasyon_rapor.pdf"'
#         response.write(pdf)
#         start_date=None,
#         end_date=None
#         return response
#     else:
#         return HttpResponse("Geçersiz istek methodu: Sadece GET isteği kabul edilir.")


def fis_kontrol(request):
    fis = None
    siparisler = None
    form = FisKontrolForm()  # Form örneğini oluşturun
    siparisler_tüm = None
    fis_tüm = None
    message = None  # Mesaj değişkeni

    if request.method == 'POST':
        form = FisKontrolForm(request.POST)
        if form.is_valid():
            fis_numarasi = form.cleaned_data['fis_num']
            if fis_numarasi == -1:
                 siparisler_tüm = Sipariş.objects.all()
                 fis_tüm = Fiş.objects.all()
                 # Mesajı ayarlayın
                 message = "Tüm fişler listelendi."
            else:
                siparisler = Sipariş.objects.filter(siparis_fis_num=fis_numarasi)
                fis = Fiş.objects.filter(fis_numarasi=fis_numarasi).first()
                if fis:
                    # Belirli bir fiş bulunduysa mesajı ayarlayın
                    message = f"Fiş Numarası: #{fis.fis_numarasi} için siparişler listelendi."
                else:
                    # Belirli bir fiş numarasına sahip fiş bulunamadıysa mesajı ayarlayın
                    message = f"Fiş Numarası: #{fis_numarasi} için fiş bulunamadı."

    context = {
        'siparisler_tüm': siparisler_tüm,
        'fis_tüm': fis_tüm,
        'fis': fis,
        'siparisler': siparisler,
        'form': form,
        'message': message,  # Mesajı context içinde gönderin
    }
    return render(request, 'fis_kontrol.html', context)

def garson_olustur(request):
    today = timezone.now
    if request.method == 'POST':
        form = GarsonForm(request.POST)

        if form.is_valid():
            garson = form.save()
            messages.success(request, 'Garson başarıyla oluşturuldu.')  # Başarı mesajı
            return redirect('garson_detay', pk=garson.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')  # Hata mesajı

    else:
        form = GarsonForm()

    context = {
        'today': today,
        'form': form,
    }
    return render(request, 'garson_olustur.html', context)
def garsonlar(request):
    garsonlar = Garson.objects.filter(durum=0)
    cikanlar = Garson.objects.filter(durum=1)
    context = {
        'cikanlar':cikanlar,
        'garsonlar':garsonlar,
    }
    return render(request, 'garsonlar.html', context)


def garsonu_isten_cikar(request, id):
    garson = get_object_or_404(Garson, id=id)

    if request.method == 'POST':
        # Garsonu işten çıkar
        garson.is_active = False
        garson.durum = 1
        garson.ayrilma_tarihi = timezone.now()
        garson.save()

        # Garsonun kodunu başına "00." ekleyin
        garson.kod = f"00.{garson.kod}"
        garson.save()
        return redirect('garsonlar')  # İşlem tamamlandığında bir başka sayfaya yönlendirin

    return render(request, 'garsonlar.html')
def garsonu_geri_al(request, id):
    garson = get_object_or_404(Garson, id=id)

    if request.method == 'POST':
        # Garsonun kodundan başındaki "00." ekini kaldırın
        garson.kod = garson.kod.replace("00.", "", 1)
        garson.save()

        # Garsonu tekrar aktif hale getirin
        garson.is_active = True
        garson.durum = 0
        garson.save()

        return redirect('garsonlar')  # İşlem tamamlandığında bir başka sayfaya yönlendirin

    return render(request, 'garsonlar')  # "Geri al" işlemi için bir HTML şablonu oluşturun
from django.contrib.auth import authenticate, login
def garson_login(request):
    if request.method == 'POST':
        form = GarsonLoginForm(request.POST)
        if form.is_valid():
            kod = form.cleaned_data['kod']
            password = form.cleaned_data['password']
            
            # Garsonları veritabanınızdan çekin (örneğin, Garson modelini kullanarak)
            try:
                garson = Garson.objects.get(kod=kod)
            except Garson.DoesNotExist:
                garson = None
            
            if garson is not None and garson.password == password:
                # Kullanıcı doğrulandı, oturumu başlatın
                request.session['garson_kod'] = garson.kod
                request.session['garson_adi'] = garson.adi
                return redirect('index')  # Başarılı giriş sonrası yönlendirme yapabilirsiniz
            else:
                # Kimlik doğrulama başarısız olduğunda bir hata mesajı ekleyebilirsiniz
                messages.error(request, 'Geçersiz giriş bilgileri. Lütfen tekrar deneyin.')
    else:
        form = GarsonLoginForm()
    
    return render(request, 'garson_login.html', {'form': form})
def garson_logout(request):
    # Oturumu temizle (session flush)
    request.session.flush()
    
    # Tüm aktif oturumları sonlandır (isteğe bağlı)
    #Session.objects.filter(session_key=request.session.session_key).delete()
    
    return redirect('garson_giris')
def rezervasyon_listesi(request):
    today = timezone.now().strftime('%Y-%m-%d')
    masalar = Masa.objects.all()
    
    rezervasyonlar = Rezervasyon.objects.filter(tarih__gte=today, durum=0)
    paginator = Paginator(rezervasyonlar, 25)
    update_form = ReservationUpdateForm()
    sayfa_numarasi = request.GET.get("page")
    sayfa_rez = paginator.get_page(sayfa_numarasi)
    context = {
        'sayfa_numarasi':sayfa_numarasi,
        'sayfa_rez':sayfa_rez,
        'paginator':paginator,
        'masalar':masalar,
        'update_form':update_form,
        'today':today,
        'rezervasyonlar':rezervasyonlar
    }
    print(rezervasyonlar)
    return render(request, 'rezervasyon_listesi.html',context)
def siparis_iptal(request, id):
    siparis = get_object_or_404(Sipariş, id=id)

    # İptal edilecek miktar (örneğin, 1 adet)
    iptal_miktar = 1

    # İptal edilen miktar, siparişin miktarından çıkartılır
    if siparis.miktar > iptal_miktar:
        siparis.miktar -= iptal_miktar
    else:
        # İptal edilecek miktar, sipariş miktarından fazla ise sipariş tamamen iptal edilir
        siparis.miktar = 0

    siparis.save()

    # Sipariş iptal edildikten sonra başka bir sayfaya yönlendirme yapılabilir
    return redirect('kasa_islem')

def masa_duzelt(request):
    masalar = Masa.objects.all()
    products = Product.objects.all()
    categories = Category.objects.all()
    if request.method == 'POST':
        masa_id = request.POST.get('selected_masa')

        if masa_id:
            masa = get_object_or_404(Masa, id=masa_id)
            fisler = Fiş.objects.filter(masa=masa)

            siparisler = []
            for fis in fisler:
                siparisler_fis = Sipariş.objects.filter(siparis_fis_num=fis.fis_numarasi)
                siparisler.append({
                    'fis': fis,
                    'siparisler': siparisler_fis
                })
                print(siparisler,'\n')

            context = {

                'categories':categories,
                'products':products,
                'masalar': masalar,
                'masa': masa,
                'fisler': fisler,
                'siparisler': siparisler,
            }

            return render(request, 'özel/masa_düzelt.html', context)

    # Gerekli diğer işlemleri yap ve template'e geri dön
    masalar = Masa.objects.all()
    return render(request, 'özel/masa_düzelt.html', {'masalar': masalar})
def fis_duzelt(request):
    urunler = Product.objects.all()
    if request.method == "POST":
        fis_numarasi = request.POST.get("fis_numarasi")
        
        try:
            fis = Fiş.objects.get(fis_numarasi=fis_numarasi)
            siparisler = Sipariş.objects.filter(siparis_fis_num=fis_numarasi)
            masa_num = fis.masa
        except Fiş.DoesNotExist:
            messages.error(request, 'Böyle bir fiş bulunamadı.')
            return redirect('fis_listele')
        
        context = {
            'urunler':urunler,
            'siparisler': siparisler,
            'fis': fis,
            'masa_num':masa_num,
        }
        return render(request, 'özel/fis_duzelt.html', context)
    else:
        # Eğer request method POST değilse, fis_listele sayfasına yönlendir.
        return redirect('fis_listele')
def fis_listele(request):
    fisler = Fiş.objects.all()
    context = {
                'fisler': fisler,

            }

    return render(request, 'özel/fis_listele.html', context)
from django.db import transaction
@transaction.atomic
def miktari_düzenle(request, fis_numarasi,urun_id):
    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith('miktar_'):
                urun_id = key.replace('miktar_', '')
                siparis = get_object_or_404(Sipariş, siparis_fis_num=fis_numarasi, urun_id=urun_id)
                siparis.miktar = value
                fis = get_object_or_404(Fiş, fis_numarasi =siparis.siparis_fis_num)
                fis.tutar = int(fis.tutar) + int(value) * int(siparis.urun.price)

                print(fis.tutar)
                fis.save()
                # Kasadan o işlemi bul #fiş num masa num siparis fis aynı olunca kasayı siparişe bağladım
                kasa = get_object_or_404(Kasa, masa_num=siparis.masa_num, fis_num=siparis.siparis_fis_num,siparis=siparis)
                kasa.tutar = int(value)*(siparis.urun.price)
                
                
                siparis.save()
                print(kasa.tutar)
                siparis.odenen_miktar = value
                kasa.aciklama = f'{siparis.masa_num} masasının {siparis.urun} ürünün {siparis.miktar} adeti ödendi'
                kasa.save()
                siparis.save()
        return redirect('fis_düzelt')

def rezervasyon_guncelle(request, id):
    masalar = Masa.objects.all()
    rezervasyon = get_object_or_404(Rezervasyon, id=id)

    if request.method == 'POST':
        update_form = ReservationUpdateForm(request.POST, instance=rezervasyon)

        if update_form.is_valid():
            # Tarih alanını "datetime-local" türüne uygun formata çevir

            update_form.save()
            return redirect('rezervasyon_listesi')
    else:
        update_form = ReservationUpdateForm(instance=rezervasyon)

    context = {
        'masalar': masalar,
        'rezervasyon': rezervasyon,  # Eklendi
        'update_form': update_form,
    }
    print(update_form.errors)
    return render(request, 'index.html', context)  # 'rezervasyon_guncelle.html' gibi bir template kullanılabilir

def kasa_düzelt(request):
    form = TarihSecForm(request.GET or None)
    
    # Bugünün tarihini al
    bugun = datetime.now().date()
    secilen_tarih =  bugun
    print(bugun)
    # Bugünün kasa işlemlerini filtrele
    gunluk_kasa = Kasa.objects.filter(islem_tarihi=bugun,durum=0)

    
    secilen_kasa = Kasa.objects.filter(islem_tarihi=secilen_tarih,durum=0)
    kasa_toplami = secilen_kasa.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    # Eğer form gönderilmişse
    if form.is_valid():
        secilen_tarih = form.cleaned_data['secilen_tarih']
        
        # Secilen tarih objesini aware hale getir
        secilen_tarih = make_aware(datetime.combine(secilen_tarih, datetime.min.time()))
        
        # Seçilen tarihin kasa işlemlerini filtrele
        secilen_kasa = Kasa.objects.filter(islem_tarihi=secilen_tarih,durum=0)
        
        # Seçilen tarih için toplamı hesapla
        kasa_toplami = secilen_kasa.aggregate(toplam=Sum('tutar'))['toplam'] or 0
    context = {
        'secilen_tarih':secilen_tarih,
        'kasa_toplami': kasa_toplami,
        'form': form,
        'gunluk_kasa': gunluk_kasa,
        'secilen_kasa': secilen_kasa,
    }

    print(kasa_toplami)
    return render(request, 'özel/kasa_düzelt.html', context)
def kasa_islem_sil(request,id):
    if request.method == "POST":
        kasa_islem = get_object_or_404(Kasa,id=id) # hangi işlem olduğunu al 
        print('Kasa',kasa_islem.id)
        kasa_islem.durum = 1
        kasa_islem.save()
        return redirect(request.META.get('HTTP_REFERER')) 
    else:
        pass
def odeme_durumu_degistir(request,id):
    if request.method == "POST":
        kasa_islem = get_object_or_404(Kasa,id=id) # hangi işlem olduğunu al 
        if kasa_islem.odeme_durumu == "Nakit": #İşlem nakitse kredi kartı olarak değiştir
            kasa_islem.odeme_durumu = "K.Kartı"
            print(kasa_islem.odeme_durumu)
            kasa_islem.save()
        elif kasa_islem.odeme_durumu == "K.Kartı":
            kasa_islem.odeme_durumu ="Nakit"
            kasa_islem.save()
    return redirect(request.META.get('HTTP_REFERER'))

def parametre(request):
    company = Company.objects.first() 
    masalar = Masa.objects.filter(hayali_masa=True)
    
    if not masalar.exists():
        raise Http404("Masalar bulunamadı")
    
    kasa = Masa.objects.filter(kasa_masasi=True).first()
    
    printer = company.yazici_adi
    
    if request.method == "POST":
        yeni_yazici_adi = request.POST.get('yeni_yazici_adi')
        new_masa_görünümü = request.POST.get('new_masa_görünümü')
        yeni_iskonto_tutari = request.POST.get('yeni_iskonto_tutari')
        kasa_masa = request.POST.get('kasa_masa')
        
        if kasa_masa:
            masa = Masa.objects.get(id=kasa_masa)
            if kasa:
                kasa.kasa_masasi = False
                kasa.save()
            masa.kasa_masasi = True
            masa.save()
        
        yeni_ödendigi_kur_gözüksün = request.POST.get('yeni_ödendigi_kur_gözüksün')
        
        if yeni_yazici_adi:
            company.yazici_adi = yeni_yazici_adi
        company.masa_görünümü = new_masa_görünümü
        company.iskonto_tutari = yeni_iskonto_tutari
        company.ödendigi_kur_gözüksün = yeni_ödendigi_kur_gözüksün
        company.save()
        
        return redirect('parametre')  # Redirect back to the same page to show updated value

    context = {
        'printer': printer,
        'kasa': kasa,
        'masalar': masalar,
        'yazici_adi': company.yazici_adi,
        'ödendigi_kur_gözüksün': company.ödendigi_kur_gözüksün,
        'masa_görünümü': company.masa_görünümü,
        'iskonto_tutari': company.iskonto_tutari,
    }
    return render(request, 'özel/parametre.html', context)

def add_currency(request): # döviz EKLEME İŞLEMİ
    dövizler = Döviz.objects.all()
    if request.method == 'POST':
        form = AddCurrencyForm(request.POST)
        if form.is_valid():
            kod = form.cleaned_data['kodu']  # Formdan konum bilgisini al
            existing_currency = Döviz.objects.filter(kodu=kod).first()
            if existing_currency:
                messages.error(request, f"'{kod}' kodu dövizli zaten var.")
                return redirect('döviz_ekle')
            else:
                rD = requests.get("https://kur.doviz.com/")
                soupD = BeautifulSoup(rD.content, "html.parser")

                # Kod bulma işlemi
                kod_element = soupD.find("td", {"data-socket-key": kod})
                if kod_element:
                    kod_value = kod_element.text
                    # Veri bulunduğunda kayıt yapabilirsiniz
                    form.save()
                    messages.success(request, 'Kayıt Yapıldı')
                else:
                    messages.error(request, f"'{kod}' kodu bulunamadı.")
                
            return redirect('döviz_ekle')  # İşlem sonrası yine eklemeye yönlendir
        else:
            messages.error(request, form.errors)
    else:
        form = AddCurrencyForm()
    dövizler = Döviz.objects.all()
    context = {
        'dövizler':dövizler,
        'form': form,
    }
    return render(request, 'özel/döviz_ekle.html', context)
import time
def döviz_cek(request):
    döviz_degerleri = {}

    try:
        rD = requests.get("https://kur.doviz.com/")
        soupD = BeautifulSoup(rD.content, "html.parser")

        for döviz in Döviz.objects.all():
            döviz_element = soupD.find("td", {"data-socket-key": döviz.kodu, "data-socket-attr": "bid"})

            if döviz_element:
                döviz_degeri_str = döviz_element.text.strip().replace(",", ".")
                try:
                    döviz_degeri = float(döviz_degeri_str)
                    döviz.tutar = round(döviz_degeri,4)
                    döviz.save()
                    döviz_degerleri[döviz.kodu] = döviz.tutar
                except ValueError:
                    print(f"{döviz.kodu} için geçersiz sayı formatı: {döviz_degeri_str}")
            else:
                print(f"{döviz.kodu} için döviz elementi bulunamadı.")
    except requests.RequestException as e:
        print(f"Döviz çekme hatası: {e}")

    # Hata ayıklama için print ifadesi
    print('Döviz Değerleri:', döviz_degerleri)

    return redirect('döviz_ekle')

def hesap_al(request, konum, num):
    dövizler = Döviz.objects.all()
    konum_obj = get_object_or_404(Position, name=konum)
    masa = get_object_or_404(Masa, num=num, konum=konum_obj)
    
    siparisler = Sipariş.objects.filter(masa_num=masa, siparis_fis_num=masa.mevcut_fis_num)
    
    # Her bir siparişin ürün fiyatı ile miktarını çarp ve toplamı al
    siparisler = siparisler.annotate(siparis_toplami=ExpressionWrapper(F('urun__price') * F('miktar'), output_field=DecimalField()))
    
    # Siparişlerin toplamını al
    total_account = siparisler.aggregate(toplam_siparis=Sum('siparis_toplami'))['toplam_siparis'] or 0
    
    context = {
        'dövizler':dövizler,
        'masa': masa,
        'konum_obj': konum_obj,
        'total_account': total_account,
        'siparisler': siparisler,
    }
    
    return render(request, 'hesap_al.html', context)
from django.core.serializers import serialize
# hesapları ayırda masa numarasının yanına [1] ekliyor
# fiş numarası aynı fiş numarası verilmeyecek fiş numarası sıraya göre devam edecek yada masa oluşturulduğu gibi fişte oluşturacak o fiş üstünden deevam edecek
# hesap ödendiğinde masanın geçici durumu true ise masa silinecek !!!! modelden bak do nothing olucak daha sonra masa silindiğinde fişi silmeyecek.
#
# hesaplar ayrılırken ödenen miktar sipariş miktarina eşitse o üründe ayrılma olmayacak hepsi ödendiği için.
def hesaplari_ayir(request):
    if request.method == 'POST':
        masa_num = request.POST.get('masa_num')
        masa = get_object_or_404(Masa, num=masa_num)
        gizli_adet = request.POST.get('gizli_adet')
        masa.gecici_sira += 1
        masa.save()
        
        # Yeni fiş oluşturun
        fis = Fiş.objects.create(
            masa=masa,
            tutar=0,
            durum=0,
            indirim=0,
        )
        
        yeni_masa = Masa.objects.create(
            konum=masa.konum,
            num=f"{masa.num}[{masa.gecici_sira}]",
            durum=masa.durum,
            rez_durum=0,
            mevcut_fis_num=fis.fis_numarasi,
            qrcode=None,
            gecici=True
        )

        # Yeni masa nesnesini kaydedin
        yeni_masa.save()

        # Her bir siparişin adet ve sipariş ID değerlerini ayrı ayrı listelere ekleyin
        adet_values = []
        siparis_id_values = []
        total_siparis = 0
        for key, value in request.POST.items():
            if key.startswith('adet_'):
                adet_values.append(value)
                siparis_id = key.replace('adet_', '')
                siparis_id_values.append(request.POST.get('siparis_id_' + siparis_id))
                total_siparis += 1

        print('Sipariş Adetleri:', adet_values)
        print('Sipariş ID\'leri:', siparis_id_values)
        print(f'Toplam Sipariş Sayısı: {total_siparis}')
        print(f'Masa Numarası: {masa_num}, Gizli Adet: {gizli_adet}')
        print('Masa Numarası AJAXTAN GELENE GÖRE:', masa_num)

        for i in range(total_siparis):
            adet = adet_values[i]
            siparis_id = siparis_id_values[i]

            # Ürün nesnesini çekin
            urun_id = request.POST.get('urun_id_' + siparis_id)
            siparis = get_object_or_404(Sipariş, id=siparis_id)

            print(f"Sipariş ID: {siparis_id}, Ürün ID: {siparis.urun}")
            urun1 = siparis.urun.id
            urun = get_object_or_404(Product, id=siparis.urun.id)
            
            # Siparişin miktarını güncelle
            siparis.miktar = int(siparis.miktar) - int(adet)
            print('Sipariş Miktarı', siparis.miktar, 'Adet', adet)
            
            # Adet 0 değilse yeni sipariş oluştur
            if int(adet) != 0:
                # Sipariş nesnesini oluşturun ve veritabanına kaydedin
                yeni_siparis = Sipariş.objects.create(
                    masa_num=yeni_masa,
                    miktar=adet,
                    siparis_fis_num=fis.fis_numarasi,
                    urun=urun
                )

                # Yeni siparişi kaydedin
                yeni_siparis.save()

            # Siparişi kaydedin
            siparis.save()

        return HttpResponse("İşlem başarılı.")
        
        # Diğer işlemleri gerçekleştir

    return HttpResponse("İşlem başarılı.")
def gecici_masa_sil(request):
    masalar = Masa.objects.filter(gecici=True,)
    masalar.delete()
    return render(request,'index.html')
import matplotlib.pyplot as plt
from collections import Counter
from django.http import HttpResponse
from django.shortcuts import render
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
from collections import Counter
import matplotlib.pyplot as plt, mpld3
import io
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import mpld3
from django.template.loader import get_template
from django.http import HttpResponse
from django.shortcuts import render
from xhtml2pdf import pisa
import io
import matplotlib.pyplot as plt
import mpld3
from django.db.models import Sum

from django.template.loader import get_template, render_to_string
from django.http import HttpResponse
from django.shortcuts import render
from xhtml2pdf import pisa
import io
import matplotlib.pyplot as plt
import mpld3
from django.db.models import Sum

from django.template.loader import get_template, render_to_string
from django.http import HttpResponse
from django.shortcuts import render
from xhtml2pdf import pisa
import io
import matplotlib.pyplot as plt
import mpld3
from django.db.models import Sum
from django.shortcuts import render
from django.db.models import Sum
from .models import Product, Sipariş
import matplotlib.pyplot as plt
import mpld3
from io import BytesIO
import base64
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

def pasta_rapor(request):
    if request.method == 'POST':
        urunler = Product.objects.all()
        pdf_istek = request.POST.get('pdf')
        # Satış miktarlarını ve etiketleri bul
        satış_miktarları = []
        etiketler = []
        
        for urun in urunler:
            siparisler = Sipariş.objects.filter(urun=urun, miktar__gt=0)
            toplam_siparis = siparisler.aggregate(toplam_siparis=Sum('miktar'))['toplam_siparis'] or 0
            
            if toplam_siparis > 0:
                etiketler.append(urun.name)
                satış_miktarları.append(toplam_siparis)
        
        # Pasta grafiğini oluştur
        fig, ax = plt.subplots()
        ax.pie(satış_miktarları, labels=etiketler, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Daireyi düzgün bir daire olarak ayarla

        # PDF dosyasına benzersiz bir ad oluştur
        pdf_ad = f'grafik_{uuid.uuid4().hex}.pdf'

        # Grafiği PDF'e dönüştür
        pdf_buffer = BytesIO()
        fig.savefig(pdf_buffer, format='pdf')
        pdf_buffer.seek(0)
        grafik_html = mpld3.fig_to_html(fig)
        
        # PDF dosyasını HttpResponse ile döndür
        if pdf_istek == 'on':
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename={pdf_ad}'
            pdf_buffer.close()
            
            return response

    else:
        grafik_html = None

    # Görüntülenmesi için grafik HTML'ini gönder
    return render(request, 'grafik.html', {'grafik_html': grafik_html})
def toplam_formatter(pct, all_values, currency):
    total = sum(all_values)
    val = int(round(pct * total / 100.0))
    return f'{val} {currency}'

def kasa_pasta(request):
  pass
from django.db.models import Sum

from django.db.models import Sum

def urun_satis_rapor(request):
    siparisler = None
    urunler = Product.objects.all()
    kasalar = None
    today = datetime.today().strftime('%Y-%m-%d')
    start_date = None
    end_date = None
    error_message = None
    
    if request.method == "POST":
        günlük_satis_raporu = request.POST.get('günlük_satis_raporu')
        print('Günlük Satiş CB', günlük_satis_raporu)
        ürün_satis_raporu = request.POST.get('ürün_satis_raporu')
        print('Ürün Satiş CB', ürün_satis_raporu)
        kasa_rapor = request.POST.get('kasa_rapor')
        print('Kasa Rapor CB', kasa_rapor)

        start_date_str = request.POST.get('start_date', '')
        end_date_str = request.POST.get('end_date', '')

        try:
            # Tarih formatını kontrol et ve datetime nesnesine çevir
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            print(start_date)
            print(end_date)

            if günlük_satis_raporu == 'on':
                siparisler = Sipariş.objects.filter(islem_tarihi__range=[start_date, end_date])
                context = {
                    'siparisler': siparisler,
                }
                return render(request, 'urun_satıs_rapor.html', context)

            elif ürün_satis_raporu == 'on':
                siparisler = None
                # Tüm ürünler için toplam satış miktarlarını al
                for urun in urunler:
                    urun.toplam_satis = Sipariş.objects.filter(urun=urun, islem_tarihi__range=[start_date, end_date]).aggregate(toplam_satis=Sum('miktar'))['toplam_satis'] or 0
                # 0 olanları filtrele
                urunler = [urun for urun in urunler if urun.toplam_satis != 0]
                context = {
                    'siparisler': siparisler,
                    'today': today,
                    'urunler': urunler,
                    'start_date': start_date,
                    'end_date': end_date,
                }
                return render(request, 'urun_satıs_rapor.html', context)

            elif kasa_rapor == 'on':
                kasalar = Kasa.objects.filter(islem_tarihi__range=[start_date, end_date])
                döviz_toplamları = {}  # Her döviz için toplamı tutacak sözlük
                for kasa in kasalar:
                    döviz_toplam = Kasa.objects.filter(
                        döviz=kasa.döviz,
                        islem_tarihi__range=[start_date, end_date]
                    ).aggregate(total_amount=Sum('tutar'))['total_amount'] or 0

                    # Her döviz için toplamı saklayın
                    döviz_toplamları[kasa.döviz] = döviz_toplam

                    print(f"{kasa.döviz} toplam tutarı: {döviz_toplam}")

                    # print(f"{kasa.döviz} toplam tutarı: {kasa.döviz_total}")
                context = {
                    'döviz_toplamları':döviz_toplamları,
                    'today':today,
                    'start_date': start_date,
                    'end_date': end_date,
                    'kasalar': kasalar,
                }
                return render(request, 'urun_satıs_rapor.html', context)

        except ValueError:
            # Tarih formatı geçersizse hata mesajı gönder
            print('Hataya Düştü')
            error_message = 'Geçersiz tarih formatı. Lütfen YYYY-MM-DD biçiminde tarih girin.'

    context = {
        'today': today,
        'error_message': error_message,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'urun_satıs_rapor.html', context)

def fise_siparis_ekle(request):
    if request.method == "POST":
        fis_num = request.POST.get('fis_numarasi')
        fis = get_object_or_404(Fiş, fis_numarasi=fis_num)

        if fis.durum == False:
            messages.error(request, 'Kapalı Fişte İşlem Yapılamaz. Fişi Açıp Tekrar Deneyin.')
            return redirect('fis_duzelt')

        urun_id = request.POST.get('urun_id')
        miktar = int(request.POST.get('miktar'))
        odendi = request.POST.get('odendi')
        odenmedi = request.POST.get('odenmedi')
        masa_num = request.POST.get('masa_num')
        masa = get_object_or_404(Masa, id=masa_num)

        if odendi:
            odeme_durumu = 'Ödendi'
        elif odenmedi:
            odeme_durumu = 'Ödenmedi'
        else:
            odeme_durumu = 'Ödenmedi'

        # Var olan siparişi sorgula
        existing_siparis = Sipariş.objects.filter(
            siparis_fis_num=fis_num,
            urun_id=urun_id,
            masa_num=masa,
            odeme_durumu=odeme_durumu,
        ).first()

        if existing_siparis:
            # Eğer varsa, miktarını güncelle
            existing_siparis.miktar += miktar
            existing_siparis.save()
        else:
            # Yoksa yeni sipariş oluştur
            Sipariş.objects.create(
                miktar=miktar,
                siparis_fis_num=fis_num,
                urun_id=urun_id,
                masa_num=masa,
                siparis_durumu=odeme_durumu,
                odenen_miktar=0,
                odeme_durumu=odeme_durumu,
                istek='Sonradan Eklenen Sipariş',
            )

    return redirect('fis_duzelt')
import json
from django.http import JsonResponse
def masa_tasi(request):
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body.decode('utf-8'))
        tasinan_masa_id = data.get('tasinan_masa')
        tasinan_masa = get_object_or_404(Masa, id=tasinan_masa_id)
        if not tasinan_masa.mevcut_fis_num:
            response_data = {
                'success': False,
                'message': 'Taşınacak masada aktif bir fiş bulunmamaktadır.',
            }
            return JsonResponse(response_data, status=400)
        tasinacak_masa_id = data.get('tasinacak_masa')
        tasinacak_masa = get_object_or_404(Masa, id=tasinacak_masa_id)

        # Eğer taşınacak masada fiş numarası yoksa, işlem yapma
        if not tasinacak_masa.mevcut_fis_num:
            response_data = {
                'success': False,
                'message': 'Taşınacak masada aktif bir fiş bulunmamaktadır.',
            }
            return JsonResponse(response_data, status=400)

        tasinan_masa_siparisler = Sipariş.objects.filter(siparis_fis_num=tasinan_masa.mevcut_fis_num)

        # Her bir siparişi taşınacak masa ile ilişkilendir
        for siparis in tasinan_masa_siparisler:
            siparis.masa_num = tasinacak_masa
            siparis.save()

        tasinacak_masa.mevcut_fis_num = tasinan_masa.mevcut_fis_num
        tasinacak_masa.durum = True
        tasinacak_masa.save() 

        tasinan_masa.durum = False
        tasinan_masa.mevcut_fis_num = None
        tasinan_masa.save()
        
        print("Taşınan Masa:", tasinan_masa)
        print("Taşınan Masa Siparişleri:", tasinan_masa_siparisler)
        print("Taşınacak Masa:", tasinacak_masa)

        response_data = {
            'success': True,
            'message': 'Masa taşıma işlemi başarılı!',
        }
        return JsonResponse(response_data)

    else:
        masalar = Masa.objects.all()
        context = {
            'masalar': masalar,
        }
        return render(request, 'test.html', context)
    pass
import json
from django.http import JsonResponse

from django.http import JsonResponse
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
@transaction.atomic
def satis_yap(request):
    grouped_products = {}
    odeme_yontemi = request.POST.get('odeme_yontemi')
    categories = Category.objects.all()
    kasa_masalari = Masa.objects.filter(kasa_masasi=True).count()
    if kasa_masalari > 1:
        messages.error(request, 'Birden Fazla Kasa Olamaz Lütfen Kasa Olacak Masayı Düzeltin')
        return redirect('parametre')
    masa = get_object_or_404(Masa,kasa_masasi=True)
    for category in categories:
        grouped_products[category] = Product.objects.filter(category=category)

    context = {
        'categories':categories,
        'grouped_products': grouped_products
        }

    if request.method == 'POST':
        print(request.method)
        print("Received data:", request.body.decode('utf-8'))
        selected_products_str = request.POST.get('selected_products')
        print(selected_products_str)
        print('Ödeme Yöntemi:', odeme_yontemi)
        print('Ödeme Yöntemi',odeme_yontemi)

        if selected_products_str is not None:
            try:
                selected_products = json.loads(selected_products_str)
                print(selected_products_str)
                company = Company.objects.first()
                kasa = company.kasa_masasi
                
                print('Ödeme Yöntemi',odeme_yontemi)

                with transaction.atomic():
                    for product in selected_products:
                        print(product)
                        urun_id = product['id']
                        print(urun_id)
                        miktar = product['quantity']
                        print(miktar)
                        try:
                            urun = Product.objects.get(id=urun_id)
                            print(urun)
                            # masa = Masa.objects.get(id=kasa)
                            # print('MASA',masa)

                            # Update table information, e.g., incrementing order number
                            # masa.mevcut_fis_num += 1
                            # masa.save()
                            # Create the order,
                            siparis = Sipariş.objects.create(
                                urun=urun,
                                masa_num=masa,
                                miktar=miktar,
                                siparis_fis_num=masa.mevcut_fis_num,
                                odenen_miktar=0,
                                siparis_durumu='Odendi',
                                odeme_durumu=odeme_yontemi,
                            )
                            tutar = siparis.miktar * urun.price
                            Kasa.objects.create(
                                    siparis=siparis,
                                    aciklama=f'Kasadan Satış {urun.name} {siparis.miktar} adeti ödendi',
                                    islem_tarihi=datetime.now(),
                                    fis_num=siparis.siparis_fis_num,
                                    masa_num=siparis.masa_num,
                                    tutar=tutar,
                                    net_tutar=siparis.urun.price * siparis.miktar,
                                    odeme_durumu=odeme_yontemi,
                                    döviz='TL',
                                    ödendigi_kur='1'
                                )
                            siparis.save()

                        except Product.DoesNotExist:
                            return JsonResponse({'error': 'Product with id {} does not exist'.format(urun_id)}, status=400)

                        except Masa.DoesNotExist:
                            return JsonResponse({'error': 'Masa with id {} does not exist'.format(kasa)}, status=400)

            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data in selected_products'}, status=400)

            # Return JsonResponse or redirect as needed
            response_data = {'message': 'Success'}
            return JsonResponse(response_data)
        else:
            response_data = {'error': 'Selected products data is missing or empty'}
            return JsonResponse(response_data, status=400)

    return render(request, 'satis_yap.html', context)

def kredi_karti_ile_kapat(request):
    return redirect(request.META.get('HTTP_REFERER'))
def generate_pdf(html_content, filename):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    HTML(string=html_content).write_pdf(response)

    return response
@login_required
def gunluk_satis(request):
    products = Product.objects.all()
    today = date.today()
    formatted_date = today.strftime("%Y-%m-%d")
    context = {
        'formatted_date': formatted_date,
        'today': today,
        'products': products,
    }

    if request.method == 'GET':
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        selected_product_id = request.GET.get('productName', '')

        gunluk_satis = {'orders': [], 'total_sales': 0, 'birim_fiyat': 0, 'toplam_fiyat': 0}

        if start_date and end_date and selected_product_id:
            try:
                birim_fiyat = Product.objects.get(id=selected_product_id).price
                
                orders = Sipariş.objects.filter(urun_id=selected_product_id, islem_tarihi__range=[start_date, end_date])
                total_quantity = orders.aggregate(Sum('miktar'))['miktar__sum']
                toplam_fiyat = orders.aggregate(Sum('miktar'))['miktar__sum'] * birim_fiyat

                gunluk_satis = {'orders': orders, 'total_quantity':total_quantity,'total_sales': len(orders), 'birim_fiyat': birim_fiyat, 'toplam_fiyat': toplam_fiyat}
            except Product.DoesNotExist:
                print(f"Seçilen Ürün Product does not exist.")
            except Exception as e:
                print(f"Hata: {e}")

        context.update({
            'gunluk_satis': gunluk_satis,
            'selected_product_id': int(selected_product_id) if selected_product_id else None,
            'start_date': start_date,
            'end_date': end_date,
        })

        if 'export_pdf' in request.GET:
            try:
                html_content = render_to_string('reports/gunluk_satis_pdf_template.html', context)
                filename = 'gunluk_satis.pdf'
                return generate_pdf(html_content, filename)
            except Exception as e:
                print(f"Hata: {e}")

        return render(request, 'reports/gunluk_satis.html', context)

    return render(request, 'reports/gunluk_satis.html', context)
from django.db.models import Count
def masa_kullanım_orani(request):
    # Her masa için sipariş sayısını hesapla (kullanılan Aggregation)
    masalar_siparis_sayisi = (
        Sipariş.objects.values('masa_num__num')  # masa_num_id'den masa_num'a eriş
        .annotate(siparis_sayisi=Count('masa_num_id'))
        .order_by('masa_num__num')
    )

    # Masa numaralarını ve sipariş sayılarını ayır
    masa_numaralari = [masa['masa_num__num'] for masa in masalar_siparis_sayisi]
    siparis_sayilari = [masa['siparis_sayisi'] for masa in masalar_siparis_sayisi]

    # Grafik oluştur
    plt.switch_backend('AGG')
    plt.figure(figsize=(10, 5))
    plt.title('Masa Sipariş Sayıları')
    plt.pie(siparis_sayilari, labels=masa_numaralari, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')  # Daireyi daha düzgün göstermek için
    plt.tight_layout()

    # Grafik resmini base64 formatına çevir
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graph = base64.b64encode(image_png).decode('utf-8')

    return render(request, 'kasa_pasta.html', {'chart': graph, 'masa_numaralari': masa_numaralari})

def kategoriye_gore_satis(request):
    categories = Category.objects.all()

    if request.method == "POST":
        selected_category_id = request.POST.get('category')
        category = get_object_or_404(Category, id=selected_category_id)

        # Seçilen kategoriye ait siparişleri çek
        order_quantities = (
            Sipariş.objects
            .filter(urun__category=category)
            .values('urun__name')
            .annotate(total_quantity=Sum('miktar'))
        )

        # Grafik oluştur
        labels = [item['urun__name'] for item in order_quantities]
        values = [item['total_quantity'] for item in order_quantities]

        plt.switch_backend('AGG')
        plt.figure(figsize=(8, 8))

        # Bar Grafik
        if 'bar' in request.POST:
            plt.bar(labels, values, color='blue')
            plt.title('Kategoriye Göre Satış Adetleri (Bar Grafik)')

        # Pasta Grafik
        elif 'pasta' in request.POST:
            plt.pie(values, labels=labels, autopct=lambda p: '{:.0f}'.format(p * sum(values) / 100), startangle=90)
            plt.title('Kategoriye Göre Satış Adetleri (Pasta Grafik)')

        # Çizgi Grafik
        elif 'cizgi' in request.POST:
            plt.plot(labels, values, marker='o', color='green', linestyle='-')
            plt.title('Kategoriye Göre Satış Adetleri (Çizgi Grafik)')

        plt.tight_layout()

        # Grafik resmini base64 formatına çevir
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        graph = base64.b64encode(image_png).decode('utf-8')
        context = {
            'graph': graph,
            'categories': categories,
            'selected_category_id': selected_category_id
        }
        return render(request, 'reports/kategoriye_gore_satis.html', context)

    context = {
        'categories': categories,
    }
    return render(request, 'reports/kategoriye_gore_satis.html', context)
def kasa_fisi_yazdir(request, id):
    secilen_fis = get_object_or_404(Kasa, id=id)

    # HTML sayfasını render et
    html_string = render_to_string('reports/kasa_fisi_output.html', {'secilen_fis': secilen_fis})

    # HTML sayfasını PDF'ye dönüştür
    pdf_file = HTML(string=html_string).write_pdf()

    # HttpResponse ile PDF'yi döndür
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=kasa_fisi_{secilen_fis.fis_num}.pdf'
    response.write(pdf_file)

    return response