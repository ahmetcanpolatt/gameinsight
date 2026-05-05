import csv
import io
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Q
from django.db.models.functions import ExtractMonth
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.contrib import messages

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Game, Platform, Genre
from .forms import GameForm

from django.core.mail import EmailMessage
from io import BytesIO

import requests
from django.conf import settings

import requests
from django.conf import settings

import requests
from django.conf import settings
from django.contrib import messages

from django.db.models import Sum
from django.db.models import Sum, Avg, Count
from django.db.models.functions import ExtractMonth, ExtractYear

from django.conf import settings
from django.core.mail import EmailMessage

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from django.db.models import Sum, Avg, Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.conf import settings
from django.core.mail import EmailMessage

from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


@login_required
def dashboard(request):
    games = Game.objects.filter(user=request.user)

    platform = request.GET.get('platform')
    genre = request.GET.get('genre')
    query = request.GET.get('q')

    if platform:
        games = games.filter(platform__name=platform)

    if genre:
        games = games.filter(genre__name=genre)

    if query:
        games = games.filter(
            Q(name__icontains=query) |
            Q(platform__name__icontains=query) |
            Q(genre__name__icontains=query)
        )

    sort = request.GET.get('sort', 'purchase_date')
    direction = request.GET.get('direction', 'desc')

    allowed_sorts = {
        'name': 'name',
        'price': 'price',
        'purchase_date': 'purchase_date',
        'playtime_hours': 'playtime_hours',
        'platform': 'platform__name',
        'genre': 'genre__name',
    }

    sort_field = allowed_sorts.get(sort, 'purchase_date')

    if direction == 'asc':
        games = games.order_by(sort_field)
    else:
        games = games.order_by(f'-{sort_field}')

    total_spent = games.aggregate(Sum('price'))['price__sum'] or 0
    total_spent = round(float(total_spent), 2)

    average_price = games.aggregate(Avg('price'))['price__avg'] or 0
    average_price = round(float(average_price), 2)

    total_games = games.count()
    total_playtime = games.aggregate(Sum('playtime_hours'))['playtime_hours__sum'] or 0

    cost_per_hour = 0
    if total_playtime and total_spent:
        cost_per_hour = round(float(total_spent) / float(total_playtime), 2)

    average_playtime = 0
    if total_games > 0:
        average_playtime = round(float(total_playtime) / float(total_games), 2)

    most_expensive_game_obj = games.order_by('-price').first()
    most_expensive_game = most_expensive_game_obj.name if most_expensive_game_obj else '-'

    most_played_game_obj = games.order_by('-playtime_hours').first()
    most_played_game = most_played_game_obj.name if most_played_game_obj else '-'

    latest_game_obj = games.order_by('-purchase_date').first()
    latest_game = latest_game_obj.name if latest_game_obj else '-'

    top_genre_data = (
        games.values('genre__name')
        .annotate(total_spent=Sum('price'))
        .order_by('-total_spent')
        .first()
    )
    top_genre = top_genre_data['genre__name'] if top_genre_data else '-'
    recommended_games = []

    most_played_game_for_recommendation = Game.objects.filter(user=request.user).order_by('-playtime_hours').first()

    if most_played_game_for_recommendation:
        search_query = f"{most_played_game_for_recommendation.name} {most_played_game_for_recommendation.genre.name}"
        recommended_games = get_recommendations_from_rawg(search_query)

    top_platform_data = (
        games.values('platform__name')
        .annotate(game_count=Count('id'))
        .order_by('-game_count')
        .first()
    )
    top_platform = top_platform_data['platform__name'] if top_platform_data else '-'

    longest_played_game_obj = games.order_by('-playtime_hours').first()
    longest_played_game = longest_played_game_obj.name if longest_played_game_obj else '-'

    genre_data = games.values('genre__name').annotate(count=Count('id')).order_by('genre__name')
    genre_labels = [item['genre__name'] for item in genre_data]
    genre_counts = [item['count'] for item in genre_data]

    platform_data = games.values('platform__name').annotate(count=Count('id')).order_by('platform__name')
    platform_labels = [item['platform__name'] for item in platform_data]
    platform_counts = [item['count'] for item in platform_data]

    from django.db.models.functions import ExtractMonth, ExtractYear

    monthly_data = Game.objects.annotate(
        month=ExtractMonth('purchase_date'),
        year=ExtractYear('purchase_date')
    ).values('year', 'month').annotate(
        total=Sum('price')
    ).order_by('year', 'month')

    month_names = {
        1: 'Ocak',
        2: 'Şubat',
        3: 'Mart',
        4: 'Nisan',
        5: 'Mayıs',
        6: 'Haziran',
        7: 'Temmuz',
        8: 'Ağustos',
        9: 'Eylül',
        10: 'Ekim',
        11: 'Kasım',
        12: 'Aralık',
    }

    monthly_labels = [
        f"{item['year']}-{str(item['month']).zfill(2)}"
        for item in monthly_data if item['month']
    ]
    monthly_totals = [float(item['total']) for item in monthly_data if item['month']]

    platforms = Game.objects.filter(user=request.user).values_list('platform__name', flat=True).distinct()
    genres = Game.objects.filter(user=request.user).values_list('genre__name', flat=True).distinct()
    top_played_games = Game.objects.filter(user=request.user).order_by('-playtime_hours')[:10]

    paginator = Paginator(games, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'page_obj': page_obj,
        'total_spent': total_spent,
        'average_price': average_price,
        'total_games': total_games,
        'total_playtime': total_playtime,
        'cost_per_hour': cost_per_hour,
        'average_playtime': average_playtime,
        'most_expensive_game': most_expensive_game,
        'most_played_game': most_played_game,
        'latest_game': latest_game,
        'top_genre': top_genre,
        'top_platform': top_platform,
        'longest_played_game': longest_played_game,
        'platforms': platforms,
        'genres': genres,
        'genre_labels': genre_labels,
        'genre_counts': genre_counts,
        'platform_labels': platform_labels,
        'platform_counts': platform_counts,
        'monthly_labels': monthly_labels,
        'monthly_totals': monthly_totals,
        'selected_platform': platform or '',
        'selected_genre': genre or '',
        'query': query or '',
        'sort': sort,
        'direction': direction,
        'top_played_games': top_played_games,
        'recommended_games': recommended_games,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'games/partials/game_list_section.html', context)

    return render(request, 'games/dashboard.html', context)

@login_required
def library(request):
    games = Game.objects.filter(user=request.user)

    platform = request.GET.get('platform')
    genre = request.GET.get('genre')
    query = request.GET.get('q')

    if platform:
        games = games.filter(platform__name=platform)

    if genre:
        games = games.filter(genre__name=genre)

    if query:
        games = games.filter(
            Q(name__icontains=query) |
            Q(platform__name__icontains=query) |
            Q(genre__name__icontains=query)
        )

    sort = request.GET.get('sort', 'purchase_date')
    direction = request.GET.get('direction', 'desc')

    allowed_sorts = {
        'name': 'name',
        'price': 'price',
        'purchase_date': 'purchase_date',
        'playtime_hours': 'playtime_hours',
        'platform': 'platform__name',
        'genre': 'genre__name',
    }

    sort_field = allowed_sorts.get(sort, 'purchase_date')

    if direction == 'asc':
        games = games.order_by(sort_field)
    else:
        games = games.order_by(f'-{sort_field}')

    platforms = Game.objects.filter(user=request.user).values_list('platform__name', flat=True).distinct()
    genres = Game.objects.filter(user=request.user).values_list('genre__name', flat=True).distinct()

    paginator = Paginator(games, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'games': page_obj,
        'page_obj': page_obj,
        'platforms': platforms,
        'genres': genres,
        'selected_platform': platform or '',
        'selected_genre': genre or '',
        'query': query or '',
        'sort': sort,
        'direction': direction,
        'total_games': games.count(),
    }

    return render(request, 'games/library.html', context)

@login_required
def add_game(request):
    rawg_name = request.GET.get('name', '').strip()
    rawg_platform = request.GET.get('platform', '').strip()
    rawg_genre = request.GET.get('genre', '').strip()
    image_url = request.GET.get('image', '').strip()
    rating = request.GET.get('rating', '').strip()

    initial_data = {
        'name': rawg_name,
    }

    if rawg_platform:
        platform_obj, _ = Platform.objects.get_or_create(name=rawg_platform)
        initial_data['platform'] = platform_obj.id

    if rawg_genre:
        genre_obj, _ = Genre.objects.get_or_create(name=rawg_genre)
        initial_data['genre'] = genre_obj.id

    if request.method == 'POST':
        form = GameForm(request.POST)

        if form.is_valid():
            game = form.save(commit=False)
            game.user = request.user

            if image_url:
                game.image_url = image_url

            if rating:
                game.rating = rating

            # Elle eklenen oyunda RAWG verisi yoksa otomatik getir
            if not game.image_url or not game.rating:
                rawg_data = get_game_data_from_rawg(game.name)

                if not game.image_url:
                    game.image_url = rawg_data.get("image_url")

                if not game.rating:
                    game.rating = rawg_data.get("rating")

            game.save()
            messages.success(request, 'Oyun başarıyla eklendi.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Oyun eklenemedi. Lütfen form alanlarını kontrol et.')

    else:
        form = GameForm(initial=initial_data)

    return render(request, 'games/add_game.html', {'form': form})


@login_required
def edit_game(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    if request.method == 'POST':
        form = GameForm(request.POST, instance=game)

        if form.is_valid():
            form.save()
            messages.success(request, 'Oyun bilgileri başarıyla güncellendi.')
            return redirect('dashboard')
    else:
        form = GameForm(instance=game)

    return render(request, 'games/edit_game.html', {
        'form': form,
        'game': game
    })


@login_required
def delete_game(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    if request.method == 'POST':
        game.delete()
        messages.success(request, 'Oyun başarıyla silindi.')
        return redirect('dashboard')

    return render(request, 'games/delete_game.html', {'game': game})


@login_required
def export_games_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="oyunlarim.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['name', 'platform', 'genre', 'price', 'purchase_date', 'playtime_hours'])

    games = Game.objects.filter(user=request.user).order_by('name')

    for game in games:
        writer.writerow([
            game.name,
            game.platform.name,
            game.genre.name,
            game.price,
            game.purchase_date,
            game.playtime_hours,
        ])

    return response


@login_required
def import_games_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Lütfen CSV uzantılı bir dosya yükleyin.')
            return redirect('import_games_csv')

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            imported_count = 0

            for row in reader:
                platform_name = row.get('platform', '').strip()
                genre_name = row.get('genre', '').strip()
                game_name = row.get('name', '').strip()

                if not game_name or not platform_name or not genre_name:
                    continue

                platform_obj, _ = Platform.objects.get_or_create(name=platform_name)
                genre_obj, _ = Genre.objects.get_or_create(name=genre_name)

                image_url = get_game_image_from_rawg(game_name)

                rawg_data = get_game_data_from_rawg(game_name)

                Game.objects.create(
                    user=request.user,
                    name=game_name,
                    platform=platform_obj,
                    genre=genre_obj,
                    price=row.get('price', 0),
                    purchase_date=row.get('purchase_date'),
                    playtime_hours=row.get('playtime_hours', 0),
                    image_url=rawg_data.get("image_url"),
                    rating=rawg_data.get("rating"),
                )

                imported_count += 1

            messages.success(request, f'{imported_count} kayıt başarıyla içe aktarıldı.')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'CSV aktarımı sırasında hata oluştu: {str(e)}')
            return redirect('import_games_csv')

    return render(request, 'games/import_csv.html')


@login_required
def export_analysis_csv(request):
    games = Game.objects.filter(user=request.user)

    total_spent = games.aggregate(Sum('price'))['price__sum'] or 0
    total_spent = round(float(total_spent), 2)

    average_price = games.aggregate(Avg('price'))['price__avg'] or 0
    average_price = round(float(average_price), 2)

    total_games = games.count()
    total_playtime = games.aggregate(Sum('playtime_hours'))['playtime_hours__sum'] or 0

    cost_per_hour = 0
    if total_playtime and total_spent:
        cost_per_hour = round(float(total_spent) / float(total_playtime), 2)

    average_playtime = 0
    if total_games > 0:
        average_playtime = round(float(total_playtime) / float(total_games), 2)

    most_expensive_game_obj = games.order_by('-price').first()
    most_expensive_game = most_expensive_game_obj.name if most_expensive_game_obj else '-'

    most_played_game_obj = games.order_by('-playtime_hours').first()
    most_played_game = most_played_game_obj.name if most_played_game_obj else '-'

    latest_game_obj = games.order_by('-purchase_date').first()
    latest_game = latest_game_obj.name if latest_game_obj else '-'

    top_genre_data = (
        games.values('genre__name')
        .annotate(total_spent=Sum('price'))
        .order_by('-total_spent')
        .first()
    )
    top_genre = top_genre_data['genre__name'] if top_genre_data else '-'

    top_platform_data = (
        games.values('platform__name')
        .annotate(game_count=Count('id'))
        .order_by('-game_count')
        .first()
    )
    top_platform = top_platform_data['platform__name'] if top_platform_data else '-'

    longest_played_game_obj = games.order_by('-playtime_hours').first()
    longest_played_game = longest_played_game_obj.name if longest_played_game_obj else '-'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="analiz_raporu.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['metric', 'value'])

    writer.writerow(['Toplam Harcama', total_spent])
    writer.writerow(['Toplam Oyun', total_games])
    writer.writerow(['Ortalama Fiyat', average_price])
    writer.writerow(['Toplam Oynama Süresi', total_playtime])
    writer.writerow(['Saat Başına Maliyet', cost_per_hour])
    writer.writerow(['En Pahalı Oyun', most_expensive_game])
    writer.writerow(['En Çok Oynanan Oyun', most_played_game])
    writer.writerow(['Son Satın Alınan Oyun', latest_game])
    writer.writerow(['En Çok Harcanan Tür', top_genre])
    writer.writerow(['En Çok Kullanılan Platform', top_platform])
    writer.writerow(['En Uzun Oynanan Oyun', longest_played_game])
    writer.writerow(['Ortalama Oynama Süresi', average_playtime])

    return response


@login_required
def export_analysis_pdf(request):
    games = Game.objects.filter(user=request.user)

    total_spent = games.aggregate(Sum('price'))['price__sum'] or 0
    total_spent = round(float(total_spent), 2)

    average_price = games.aggregate(Avg('price'))['price__avg'] or 0
    average_price = round(float(average_price), 2)

    total_games = games.count()
    total_playtime = games.aggregate(Sum('playtime_hours'))['playtime_hours__sum'] or 0

    cost_per_hour = 0
    if total_playtime and total_spent:
        cost_per_hour = round(float(total_spent) / float(total_playtime), 2)

    most_played = games.order_by('-playtime_hours').first()
    most_played_name = most_played.name if most_played else "-"

    most_expensive = games.order_by('-price').first()
    most_expensive_name = most_expensive.name if most_expensive else "-"

    latest_game = games.order_by('-id').first()
    latest_game_name = latest_game.name if latest_game else "-"

    top_genre = (
        games.values('genre__name')
        .annotate(total=Sum('price'))
        .order_by('-total')
        .first()
    )
    top_genre_name = top_genre['genre__name'] if top_genre else "-"

    top_platform = (
        games.values('platform__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )
    top_platform_name = top_platform['platform__name'] if top_platform else "-"

    best_value_game = None
    best_value = 999999
    worst_value_game = None
    worst_value = 0

    for game in games:
        if game.price and game.playtime_hours:
            value = float(game.price) / float(game.playtime_hours)

            if value < best_value:
                best_value = value
                best_value_game = game

            if value > worst_value:
                worst_value = value
                worst_value_game = game

    best_value_name = best_value_game.name if best_value_game else "-"
    worst_value_name = worst_value_game.name if worst_value_game else "-"

    monthly_data = (
        games.filter(purchase_date__isnull=False)
        .annotate(
            year=ExtractYear('purchase_date'),
            month=ExtractMonth('purchase_date')
        )
        .values('year', 'month')
        .annotate(total=Sum('price'))
        .order_by('year', 'month')
    )

    monthly_labels = [
        f"{item['year']}-{str(item['month']).zfill(2)}"
        for item in monthly_data
    ]

    monthly_totals = [
        float(item['total'] or 0)
        for item in monthly_data
    ]

    genre_data = (
        games.values('genre__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    genre_labels = [item['genre__name'] or 'Bilinmiyor' for item in genre_data]
    genre_counts = [item['count'] for item in genre_data]

    platform_data = (
        games.values('platform__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    platform_labels = [item['platform__name'] or 'Bilinmiyor' for item in platform_data]
    platform_counts = [item['count'] for item in platform_data]

    def create_line_chart(labels, values, title, ylabel):
        img_buffer = BytesIO()
        plt.figure(figsize=(7, 3.2))
        plt.plot(labels, values, marker='o')
        plt.title(title)
        plt.ylabel(ylabel)
        plt.xticks(rotation=35, ha='right')
        plt.grid(True, alpha=0.25)
        plt.tight_layout()
        plt.savefig(img_buffer, format='png', dpi=150)
        plt.close()
        img_buffer.seek(0)
        return img_buffer

    def create_bar_chart(labels, values, title, ylabel):
        img_buffer = BytesIO()
        plt.figure(figsize=(7, 3.2))
        plt.bar(labels, values)
        plt.title(title)
        plt.ylabel(ylabel)
        plt.xticks(rotation=25, ha='right')
        plt.grid(axis='y', alpha=0.25)
        plt.tight_layout()
        plt.savefig(img_buffer, format='png', dpi=150)
        plt.close()
        img_buffer.seek(0)
        return img_buffer

    monthly_chart = None
    genre_chart = None
    platform_chart = None

    if monthly_labels and monthly_totals:
        monthly_chart = create_line_chart(
            monthly_labels,
            monthly_totals,
            "Aylik Harcama Grafigi",
            "TL"
        )

    if genre_labels and genre_counts:
        genre_chart = create_bar_chart(
            genre_labels,
            genre_counts,
            "Tur Bazli Oyun Dagilimi",
            "Oyun Sayisi"
        )

    if platform_labels and platform_counts:
        platform_chart = create_bar_chart(
            platform_labels,
            platform_counts,
            "Platform Bazli Oyun Dagilimi",
            "Oyun Sayisi"
        )

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, y, "GameInsight Analiz Raporu")

    y -= 30
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Kullanici: {request.user.username}")
    y -= 20
    p.drawString(50, y, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    y -= 35

    report_lines = [
        "----- GENEL OZET -----",
        f"Toplam Harcama: {total_spent} TL",
        f"Toplam Oyun: {total_games}",
        f"Ortalama Fiyat: {average_price} TL",
        f"Toplam Oynama Suresi: {total_playtime} saat",
        f"Saat Basina Maliyet: {cost_per_hour} TL",
        "",
        "----- OYUN ANALIZI -----",
        f"En Cok Oynanan Oyun: {most_played_name}",
        f"En Pahali Oyun: {most_expensive_name}",
        f"Son Eklenen Oyun: {latest_game_name}",
        f"En Verimli Oyun: {best_value_name}",
        f"En Kotu Yatirim: {worst_value_name}",
        "",
        "----- TERCIH ANALIZI -----",
        f"En Cok Para Harcanan Tur: {top_genre_name}",
        f"En Cok Kullanilan Platform: {top_platform_name}",
    ]

    for line in report_lines:
        if y < 60:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)

        if line.startswith("-----"):
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, line)
            p.setFont("Helvetica", 11)
        else:
            p.drawString(50, y, line)

        y -= 20

    charts = [monthly_chart, genre_chart, platform_chart]

    for chart in charts:
        if chart:
            p.showPage()
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, height - 50, "Grafik Analizi")

            image = ImageReader(chart)
            p.drawImage(
                image,
                45,
                260,
                width=500,
                height=260,
                preserveAspectRatio=True,
                mask='auto'
            )

    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.35, 0.35, 0.35)
    p.drawString(50, 35, "GameInsight - Otomatik Analiz Raporu")

    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="gameinsight_analiz_raporu.pdf"'
    return response

@login_required
def send_analysis_report_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            games = Game.objects.filter(user=request.user)

            total_spent = games.aggregate(Sum('price'))['price__sum'] or 0
            total_spent = round(float(total_spent), 2)

            average_price = games.aggregate(Avg('price'))['price__avg'] or 0
            average_price = round(float(average_price), 2)

            total_games = games.count()
            total_playtime = games.aggregate(Sum('playtime_hours'))['playtime_hours__sum'] or 0

            cost_per_hour = 0
            if total_playtime and total_spent:
                cost_per_hour = round(float(total_spent) / float(total_playtime), 2)

            most_played = games.order_by('-playtime_hours').first()
            most_played_name = most_played.name if most_played else "-"

            most_expensive = games.order_by('-price').first()
            most_expensive_name = most_expensive.name if most_expensive else "-"

            latest_game = games.order_by('-id').first()
            latest_game_name = latest_game.name if latest_game else "-"

            best_value_game = None
            best_value = 999999

            worst_value_game = None
            worst_value = 0

            for game in games:
                if game.price and game.playtime_hours:
                    value = float(game.price) / float(game.playtime_hours)

                    if value < best_value:
                        best_value = value
                        best_value_game = game

                    if value > worst_value:
                        worst_value = value
                        worst_value_game = game

            best_value_name = best_value_game.name if best_value_game else "-"
            worst_value_name = worst_value_game.name if worst_value_game else "-"

            top_genre = (
                games.values('genre__name')
                .annotate(total=Sum('price'))
                .order_by('-total')
                .first()
            )
            top_genre_name = top_genre['genre__name'] if top_genre else "-"

            top_platform = (
                games.values('platform__name')
                .annotate(count=Count('id'))
                .order_by('-count')
                .first()
            )
            top_platform_name = top_platform['platform__name'] if top_platform else "-"

            # -----------------------------
            # GRAFIK VERILERI
            # -----------------------------

            monthly_data = (
                games.filter(purchase_date__isnull=False)
                .annotate(
                    year=ExtractYear('purchase_date'),
                    month=ExtractMonth('purchase_date')
                )
                .values('year', 'month')
                .annotate(total=Sum('price'))
                .order_by('year', 'month')
            )

            monthly_labels = [
                f"{item['year']}-{str(item['month']).zfill(2)}"
                for item in monthly_data
            ]

            monthly_totals = [
                float(item['total'] or 0)
                for item in monthly_data
            ]

            genre_data = (
                games.values('genre__name')
                .annotate(count=Count('id'))
                .order_by('-count')
            )

            genre_labels = [
                item['genre__name'] or 'Bilinmiyor'
                for item in genre_data
            ]

            genre_counts = [
                item['count']
                for item in genre_data
            ]

            platform_data = (
                games.values('platform__name')
                .annotate(count=Count('id'))
                .order_by('-count')
            )

            platform_labels = [
                item['platform__name'] or 'Bilinmiyor'
                for item in platform_data
            ]

            platform_counts = [
                item['count']
                for item in platform_data
            ]

            # -----------------------------
            # GRAFIK OLUSTURMA FONKSIYONLARI
            # -----------------------------

            def create_line_chart(labels, values, title, ylabel):
                img_buffer = BytesIO()

                plt.figure(figsize=(7, 3.2))
                plt.plot(labels, values, marker='o')
                plt.title(title)
                plt.ylabel(ylabel)
                plt.xticks(rotation=35, ha='right')
                plt.grid(True, alpha=0.25)
                plt.tight_layout()
                plt.savefig(img_buffer, format='png', dpi=150)
                plt.close()

                img_buffer.seek(0)
                return img_buffer

            def create_bar_chart(labels, values, title, ylabel):
                img_buffer = BytesIO()

                plt.figure(figsize=(7, 3.2))
                plt.bar(labels, values)
                plt.title(title)
                plt.ylabel(ylabel)
                plt.xticks(rotation=25, ha='right')
                plt.grid(axis='y', alpha=0.25)
                plt.tight_layout()
                plt.savefig(img_buffer, format='png', dpi=150)
                plt.close()

                img_buffer.seek(0)
                return img_buffer

            monthly_chart = None
            genre_chart = None
            platform_chart = None

            if monthly_labels and monthly_totals:
                monthly_chart = create_line_chart(
                    monthly_labels,
                    monthly_totals,
                    "Aylik Harcama Grafigi",
                    "TL"
                )

            if genre_labels and genre_counts:
                genre_chart = create_bar_chart(
                    genre_labels,
                    genre_counts,
                    "Tur Bazli Oyun Dagilimi",
                    "Oyun Sayisi"
                )

            if platform_labels and platform_counts:
                platform_chart = create_bar_chart(
                    platform_labels,
                    platform_counts,
                    "Platform Bazli Oyun Dagilimi",
                    "Oyun Sayisi"
                )

            # -----------------------------
            # PDF OLUSTURMA
            # -----------------------------

            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 50

            p.setFont("Helvetica-Bold", 18)
            p.drawString(50, y, "GameInsight Analiz Raporu")

            y -= 30
            p.setFont("Helvetica", 11)
            p.drawString(50, y, f"Kullanici: {request.user.username}")
            y -= 20
            p.drawString(50, y, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            y -= 35

            report_lines = [
                "----- GENEL OZET -----",
                f"Toplam Harcama: {total_spent} TL",
                f"Toplam Oyun: {total_games}",
                f"Ortalama Fiyat: {average_price} TL",
                f"Toplam Oynama Suresi: {total_playtime} saat",
                f"Saat Basina Maliyet: {cost_per_hour} TL",
                "",
                "----- OYUN ANALIZI -----",
                f"En Cok Oynanan Oyun: {most_played_name}",
                f"En Pahali Oyun: {most_expensive_name}",
                f"Son Eklenen Oyun: {latest_game_name}",
                f"En Verimli Oyun: {best_value_name}",
                f"En Kotu Yatirim: {worst_value_name}",
                "",
                "----- TERCIH ANALIZI -----",
                f"En Cok Para Harcanan Tur: {top_genre_name}",
                f"En Cok Kullanilan Platform: {top_platform_name}",
            ]

            for line in report_lines:
                if y < 60:
                    p.showPage()
                    y = height - 50
                    p.setFont("Helvetica", 11)

                if line.startswith("-----"):
                    p.setFont("Helvetica-Bold", 12)
                    p.drawString(50, y, line)
                    p.setFont("Helvetica", 11)
                else:
                    p.drawString(50, y, line)

                y -= 20

            # -----------------------------
            # PDF'E GRAFIKLERI EKLE
            # -----------------------------

            charts = [
                monthly_chart,
                genre_chart,
                platform_chart,
            ]

            for chart in charts:
                if chart:
                    p.showPage()
                    p.setFont("Helvetica-Bold", 14)
                    p.drawString(50, height - 50, "Grafik Analizi")

                    image = ImageReader(chart)
                    p.drawImage(
                        image,
                        45,
                        260,
                        width=500,
                        height=260,
                        preserveAspectRatio=True,
                        mask='auto'
                    )

            p.save()
            buffer.seek(0)

            # -----------------------------
            # MAIL GONDER
            # -----------------------------

            mail = EmailMessage(
                subject='GameInsight Analiz Raporu',
                body=(
                    'Merhaba,\n\n'
                    'GameInsight analiz raporunuz ekte PDF olarak yer almaktadir.\n\n'
                    'Raporda genel ozet, oyun analizi, tercih analizi ve grafikler bulunmaktadir.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )

            mail.attach(
                'gameinsight_analiz_raporu.pdf',
                buffer.getvalue(),
                'application/pdf'
            )

            mail.send(fail_silently=False)

            messages.success(request, 'Analiz raporu grafiklerle birlikte e-posta ile gönderildi.')
            return redirect('send_analysis_report_email')

        except Exception as e:
            messages.error(request, f'Mail gönderilirken hata oluştu: {e}')
            return redirect('send_analysis_report_email')

    return render(request, 'games/send_report.html')

@login_required
def rawg_search(request):
    query = request.GET.get('q', '')

    results = []

    if query:
        url = 'https://api.rawg.io/api/games'
        params = {
            'key': settings.RAWG_API_KEY,
            'search': query,
            'page_size': 5,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            for item in data.get('results', []):
                genres = item.get('genres', [])
                platforms = item.get('platforms', [])

                genre_name = genres[0]['name'] if genres else ''
                platform_name = platforms[0]['platform']['name'] if platforms else ''

                results.append({
                    'name': item.get('name', ''),
                    'released': item.get('released', ''),
                    'genre': genre_name,
                    'platform': platform_name,
                    'background_image': item.get('background_image', ''),
                    'rating': item.get('rating', 0),
                })

        except Exception:
            results = []

    return render(request, 'games/rawg_search.html', {
        'query': query,
        'results': results,
    })

def get_game_image_from_rawg(game_name):
    url = "https://api.rawg.io/api/games"
    params = {
        "key": settings.RAWG_API_KEY,
        "search": game_name,
        "page_size": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        results = data.get("results", [])
        if results:
            return results[0].get("background_image", "")
    except:
        return ""

    return ""

def get_game_image_from_rawg(game_name):
    url = "https://api.rawg.io/api/games"
    params = {
        "key": settings.RAWG_API_KEY,
        "search": game_name,
        "page_size": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        results = data.get("results", [])
        if results:
            return results[0].get("background_image", "")
    except Exception:
        return ""

    return ""

@login_required
def fetch_game_image(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    image_url = get_game_image_from_rawg(game.name)

    if image_url:
        game.image_url = image_url
        game.save()
        messages.success(request, 'Kapak fotoğrafı RAWG üzerinden başarıyla eklendi.')
    else:
        messages.error(request, 'Bu oyun için RAWG üzerinde kapak fotoğrafı bulunamadı.')

    return redirect('edit_game', game_id=game.id)

def get_game_rating_from_rawg(game_name):
    url = "https://api.rawg.io/api/games"
    params = {
        "key": settings.RAWG_API_KEY,
        "search": game_name,
        "page_size": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        results = data.get("results", [])
        if results:
            return results[0].get("rating", None)
    except Exception:
        return None

    return None

@login_required
def fetch_game_rating(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    rating = get_game_rating_from_rawg(game.name)

    if rating:
        game.rating = rating
        game.save()
        messages.success(request, 'RAWG puanı başarıyla eklendi.')
    else:
        messages.error(request, 'Bu oyun için RAWG puanı bulunamadı.')

    return redirect('edit_game', game_id=game.id)

def get_game_data_from_rawg(game_name):
    url = "https://api.rawg.io/api/games"
    params = {
        "key": settings.RAWG_API_KEY,
        "search": game_name,
        "page_size": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        results = data.get("results", [])

        if results:
            game = results[0]
            genres = game.get("genres", [])
            genre_name = genres[0].get("name") if genres else None

            return {
                "image_url": game.get("background_image", ""),
                "rating": game.get("rating", None),
                "genre": genre_name,
            }
    except Exception:
        pass

    return {
        "image_url": "",
        "rating": None,
        "genre": None,
    }

def get_recommendations_from_rawg(genre_name):
    url = "https://api.rawg.io/api/games"
    params = {
        "key": settings.RAWG_API_KEY,
        "search": genre_name,
        "page_size": 8,
        "ordering": "-rating"
    }

    recommendations = []

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        for item in data.get("results", []):
            recommendations.append({
                "name": item.get("name", ""),
                "rating": item.get("rating", ""),
                "image": item.get("background_image", ""),
                "released": item.get("released", ""),
            })

    except Exception:
        pass

    return recommendations

@login_required
def steam_sync(request):
    if request.method == 'POST':
        steam_id = request.POST.get('steam_id', '').strip()

        if not steam_id:
            messages.error(request, 'Steam ID boş olamaz.')
            return redirect('steam_sync')

        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

        params = {
            "key": settings.STEAM_API_KEY,
            "steamid": steam_id,
            "include_appinfo": True,
            "include_played_free_games": True,
            "format": "json",
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            steam_games = data.get("response", {}).get("games", [])

            if not steam_games:
                messages.error(request, 'Steam oyunları alınamadı. Profil veya oyun detayları gizli olabilir.')
                return redirect('steam_sync')

            steam_platform, _ = Platform.objects.get_or_create(name="Steam")
            default_genre, _ = Genre.objects.get_or_create(name="Steam Import")

            added_count = 0
            skipped_count = 0

            for steam_game in steam_games:
                game_name = steam_game.get("name")
                playtime_minutes = steam_game.get("playtime_forever", 0)
                playtime_hours = round(playtime_minutes / 60)

                if not game_name:
                    continue

                exists = Game.objects.filter(
                    user=request.user,
                    name__iexact=game_name,
                    platform=steam_platform
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                rawg_data = get_game_data_from_rawg(game_name)
                estimated_price = get_steam_estimated_price(steam_game.get("appid"))

                genre_name = rawg_data.get("genre") or "Steam Import"
                genre_obj, _ = Genre.objects.get_or_create(name=genre_name)

                Game.objects.create(
                    user=request.user,
                    name=game_name,
                    platform=steam_platform,
                    genre=genre_obj,
                    price=None,
                    estimated_price=estimated_price,
                    purchase_date="2026-01-01",
                    playtime_hours=playtime_hours,
                    image_url=rawg_data.get("image_url"),
                    rating=rawg_data.get("rating"),
                )

                added_count += 1

            messages.success(
                request,
                f'Steam senkronizasyonu tamamlandı. {added_count} oyun eklendi, {skipped_count} oyun zaten vardı.'
            )
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'Steam senkronizasyonunda hata oluştu: {str(e)}')
            return redirect('steam_sync')

    return render(request, 'games/steam_sync.html')

def get_steam_estimated_price(appid):
    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": appid,
        "cc": "tr",
        "filters": "price_overview"
    }

    try:
        response = requests.get(url, params=params, timeout=8)
        data = response.json()

        app_data = data.get(str(appid), {})

        if not app_data.get("success"):
            return None

        price_data = app_data.get("data", {}).get("price_overview")

        if not price_data:
            return None

        final_price = price_data.get("final")

        if final_price is None:
            return None

        return round(final_price / 100, 2)

    except Exception:
        return None
    

def fetch_price(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    if game.platform.name == "Steam":
        estimated_price = get_steam_estimated_price(game.steam_appid)

        if estimated_price:
            game.estimated_price = estimated_price
            game.save()
            messages.success(request, "Fiyat güncellendi.")
        else:
            messages.error(request, "Fiyat bulunamadı.")

    return redirect('edit_game', game_id=game.id)

@login_required
def fetch_game_price(request, game_id):
    game = get_object_or_404(Game, id=game_id, user=request.user)

    messages.error(request, 'Tahmini fiyat şu an sadece Steam senkronizasyonu ile gelen oyunlarda otomatik alınabilir.')
    return redirect('edit_game', game_id=game.id)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    return render(request, 'games/home.html')