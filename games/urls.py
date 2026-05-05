from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add/', views.add_game, name='add_game'),
    path('edit/<int:game_id>/', views.edit_game, name='edit_game'),
    path('delete/<int:game_id>/', views.delete_game, name='delete_game'),
    path('export/csv/', views.export_games_csv, name='export_games_csv'),
    path('import/csv/', views.import_games_csv, name='import_games_csv'),
    path('export/analysis/', views.export_analysis_csv, name='export_analysis_csv'),
    path('export/analysis-pdf/', views.export_analysis_pdf, name='export_analysis_pdf'),
    path('send/report/', views.send_analysis_report_email, name='send_analysis_report_email'),
    path('rawg/search/', views.rawg_search, name='rawg_search'),
    path('fetch-image/<int:game_id>/', views.fetch_game_image, name='fetch_game_image'),
    path('library/', views.library, name='library'),
    path('fetch-rating/<int:game_id>/', views.fetch_game_rating, name='fetch_game_rating'),
    path('steam/sync/', views.steam_sync, name='steam_sync'),
    path('fetch-price/<int:game_id>/', views.fetch_game_price, name='fetch_game_price'),
]