import gradio as gr
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webview  # The desktop window engine
import threading
import time

from astropy.time import Time
import astropy.units as u
from astropy.coordinates import EarthLocation, get_sun, get_body
from astroplan import Observer, FixedTarget
from astroplan.moon import moon_illumination
from geopy.geocoders import Nominatim
import datetime
import warnings
from astroplan import TargetAlwaysUpWarning

warnings.filterwarnings("ignore", category=TargetAlwaysUpWarning)

def calculate_astro_schedule(loc_mode, address_str, lat_val, lon_val, obs_datetime, sun_alt_max, targets_str):
    geolocator = Nominatim(user_agent="astro_scheduler_desktop_2026")
    try:
        raw_targets = [t.strip() for t in targets_str.split(",") if t.strip()]
        if not raw_targets:
            return None, "Error: Target list is completely empty."
        
        # High-contrast color palette 
        palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173'
        ]
        
        # Deduplicate targets and explicitly bind a permanent color to each name string
        unique_targets = list(dict.fromkeys(raw_targets))
        target_colors = {name: palette[i % len(palette)] for i, name in enumerate(unique_targets)}
        
        if loc_mode == "Address String":
            location = geolocator.geocode(address_str)
            if not location:
                return None, f"Error: Could not resolve address: '{address_str}'"
            lat_coords, lon_coords, alt_coords = location.latitude, location.longitude, location.altitude
            display_loc = address_str.split(',')[0]
        else:
            lat_coords, lon_coords, alt_coords = float(lat_val), float(lon_val), 0.0
            display_loc = f"Lat: {lat_coords:.2f}, Lon: {lon_coords:.2f}"

        earth_location = EarthLocation(lat=lat_coords*u.deg, lon=lon_coords*u.deg, height=alt_coords*u.m if alt_coords else 0*u.m)
        observer = Observer(location=earth_location)

        date_str = obs_datetime.split(" ")[0] if " " in obs_datetime else obs_datetime
        base_date = Time(date_str) 
        scan_start = base_date + 12 * u.hour 
        time_grid = scan_start + np.linspace(0, 18, 500) * u.hour

        sun_altaz = observer.altaz(time_grid, get_sun(time_grid))
        dark_mask = sun_altaz.alt.deg <= float(sun_alt_max)
        dark_times = time_grid[dark_mask]

        if len(dark_times) == 0:
            return None, f"Warning: No darkness window found where the Sun falls below {sun_alt_max}°."

        local_tz = datetime.datetime.now().astimezone().tzinfo
        local_datetimes = [dt.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz) for dt in dark_times.datetime.ravel()]
        window_start, window_end = local_datetimes[0], local_datetimes[-1]

        moon_illums = moon_illumination(dark_times)
        avg_moon_illum = np.mean(moon_illums) * 100.0
        moon_coords = get_body('moon', dark_times, location=earth_location)
        moon_altaz = observer.altaz(dark_times, moon_coords)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            subplot_titles=(f"Target Altitude Schedule (Min limit: 20°)", 
                                            "Target & Moon Azimuth Context"))

        for t_name in raw_targets:
            try:
                target = FixedTarget.from_name(t_name)
                altaz_positions = observer.altaz(dark_times, target)
                
                # Fetch the absolute locked color code for this target name string
                target_color = target_colors[t_name]
                
                # Top Plot: Altitude (Explicitly locked color)
                fig.add_trace(go.Scatter(
                    x=local_datetimes, y=altaz_positions.alt.deg, 
                    mode='lines', name=t_name, 
                    line=dict(color=target_color, width=3),
                    legendgroup=t_name
                ), row=1, col=1)
                
                # Bottom Plot: Azimuth (Forced to match the identical color configuration)
                fig.add_trace(go.Scatter(
                    x=local_datetimes, y=altaz_positions.az.deg, 
                    mode='lines', name=t_name, 
                    line=dict(color=target_color, width=3),
                    legendgroup=t_name, showlegend=False
                ), row=2, col=1)
                
                transit_time = observer.target_meridian_transit_time(dark_times[0], target, which='next')
                transit_local = transit_time.datetime.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)
                if window_start <= transit_local <= window_end:
                    transit_alt = observer.altaz(transit_time, target).alt.deg
                    if transit_alt > 0:
                        fig.add_trace(go.Scatter(
                            x=[transit_local], y=[transit_alt], mode='markers+text',
                            text=[transit_local.strftime('%H:%M')], textposition="top center",
                            marker=dict(size=9, symbol="diamond", color=target_color), 
                            showlegend=False, legendgroup=t_name
                        ), row=1, col=1)
            except Exception:
                pass

        # Static style rules solely for the Moon tracks
        fig.add_trace(go.Scatter(x=local_datetimes, y=moon_altaz.alt.deg, mode='lines', name='MOON', line=dict(color='#444444', width=3.5, dash='dash'), legendgroup='MOON'), row=1, col=1)
        fig.add_trace(go.Scatter(x=local_datetimes, y=moon_altaz.az.deg, mode='lines', name='MOON', line=dict(color='#444444', width=3.5, dash='dash'), legendgroup='MOON', showlegend=False), row=2, col=1)

        fig.add_shape(type="line", x0=window_start, x1=window_end, y0=20, y1=20, line=dict(color="Red", width=2, dash="dot"), row=1, col=1)

        # Clear white canvas layout settings with gridline styles explicitly defined
        fig.update_layout(
            height=620,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(showgrid=True, gridcolor="#eaeaea", linecolor="#cccccc", row=1, col=1)
        fig.update_xaxes(title_text=f"Local Time ({window_start.strftime('%Z')})", showgrid=True, gridcolor="#eaeaea", linecolor="#cccccc", row=2, col=1)
        
        fig.update_yaxes(title_text="Altitude (Degrees)", range=[0, 90], showgrid=True, gridcolor="#eaeaea", linecolor="#cccccc", row=1, col=1)
        fig.update_yaxes(title_text="Azimuth (Degrees)", range=[0, 360], tickvals=[0, 90, 180, 270, 360], ticktext=['N', 'E', 'S', 'W', 'N'], showgrid=True, gridcolor="#eaeaea", linecolor="#cccccc", row=2, col=1)

        status_msg = f"📍 Location: {display_loc} | 🗓️ Night: {date_str} | 🌙 Moon Illum: {avg_moon_illum:.1f}%"
        return fig, status_msg
    except Exception as e:
        return None, f"An operational error occurred: {e}"

def set_today():
    return datetime.date.today().strftime("%Y-%m-%d")

# --- Interface Setup ---
with gr.Blocks(title="Astro Scheduler Desktop") as demo:
    gr.Markdown("# 🌌 Astrophotography Target Tracking Window")
    with gr.Row():
        with gr.Column():
            loc_mode = gr.Radio(["Address String", "Lat / Lon Coordinates"], label="Location Mode", value="Address String")
            address_str = gr.Textbox(value="Wiesenstrasse 58 64331 Weiterstadt Germany", label="Address")
            with gr.Row():
                lat_val = gr.Number(value=49.90, label="Latitude")
                lon_val = gr.Number(value=8.60, label="Longitude")
        with gr.Column():
            with gr.Row():
                obs_datetime = gr.DateTime(value="2026-06-27", label="Observation Date", type="string", include_time=False)
                today_btn = gr.Button("📅 Today", size="sm")
            sun_alt_max = gr.Slider(minimum=-18, maximum=0, value=-10, step=1, label="Sun Max Altitude")
        with gr.Column():
            targets_str = gr.Textbox(value="NGC6960, NGC6992, NGC7635, M31, M42, M51, M13, M16", label="DSO Targets (Comma-separated)", lines=4)

    run_btn = gr.Button("Compute Visibility Schedule", variant="primary")
    status_output = gr.Markdown(value="Adjust inputs and hit submit to view data metrics.")
    plot_output = gr.Plot(label="Tracking Schedule")

    today_btn.click(fn=set_today, inputs=None, outputs=obs_datetime)
    run_btn.click(
        fn=calculate_astro_schedule,
        inputs=[loc_mode, address_str, lat_val, lon_val, obs_datetime, sun_alt_max, targets_str],
        outputs=[plot_output, status_output]
    )

# Global container to catch the active URL from the runner thread safely
server_config = {}

def run_gradio():
    # Capture the dynamically generated local URL directly from launch parameters
    _, local_url, _ = demo.launch(
        prevent_thread_lock=True, 
        inbrowser=False, 
        theme=gr.themes.Default()
    )
    server_config['url'] = local_url

if __name__ == "__main__":
    t = threading.Thread(target=run_gradio)
    t.daemon = True
    t.start()
    
    # Wait until the dynamic server is active and the URL is captured
    while 'url' not in server_config:
        time.sleep(0.1)
    
    print(f"🚀 Directing desktop window straight to active endpoint: {server_config['url']}")
    
    webview.create_window(
        title="Astrophotography Target Scheduler", 
        url=server_config['url'], 
        width=1250, 
        height=900, 
        resizable=True
    )
    webview.start()