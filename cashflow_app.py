#!/usr/bin/env python3
"""
Cashflow Tracker - Mac GUI Application

A desktop app for managing your personal finances with:
- CSV import with drag & drop
- Transaction editing
- Category management
- Rule management
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import sys
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import DatabaseManager
from src.parsers import detect_parser
from src.categorization import Categorizer
from src.learned_rules import LearnedRules
from src.category_mapper import CategoryMapper


def _get_data_dir() -> Path:
    """Return a writable data directory.

    When running as a frozen .app bundle (PyInstaller) the bundle directory
    itself is read-only, so we redirect user data to
    ~/Library/Application Support/CashflowTracker.
    When running from source we keep using the local data/ folder so that
    development workflow is unchanged.
    """
    if getattr(sys, 'frozen', False):
        # Running inside a PyInstaller bundle
        app_support = Path.home() / 'Library' / 'Application Support' / 'CashflowTracker'
        app_support.mkdir(parents=True, exist_ok=True)
        return app_support
    # Running from source
    return Path(__file__).parent / 'data'


class CashflowApp:
    """Main application window"""

    def __init__(self, root):
        self.root = root
        self.root.title("Cashflow Tracker")
        self.root.geometry("1200x800")

        # Initialize managers — use a writable data directory
        data_dir = _get_data_dir()
        self.db = DatabaseManager(str(data_dir / 'transactions.db'))
        self.learned_rules = LearnedRules(str(data_dir / 'learned_rules.json'))
        self.category_mapper = CategoryMapper(str(data_dir / 'category_mappings.json'))

        # Learn from existing data on startup
        self.category_mapper.learn_from_database(self.db)

        # Create UI
        self.create_menu()
        self.create_status_bar()  # Create status bar BEFORE notebook
        self.create_notebook()

        # Load initial data
        self.refresh_transactions()

    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import CSV...", command=self.import_csv, accelerator="Cmd+I")
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit, accelerator="Cmd+Q")

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Auto-Categorize All", command=self.auto_categorize_all)
        tools_menu.add_command(label="Classify Transaction Types", command=self.classify_types)
        tools_menu.add_command(label="Find Duplicates", command=self.find_duplicates)
        tools_menu.add_separator()
        tools_menu.add_command(label="Fix Duplicate Categories", command=self.fix_duplicate_categories)
        tools_menu.add_command(label="Merge Categories...", command=self.merge_categories)
        tools_menu.add_separator()
        tools_menu.add_command(label="Fix Account Names...", command=self.fix_account_names)

        # Attach menu to root window (works on all platforms)
        self.root.config(menu=menubar)

        # For macOS, also bind keyboard shortcuts
        self.root.bind('<Command-i>', lambda e: self.import_csv())
        self.root.bind('<Command-q>', lambda e: self.root.quit())

    def create_notebook(self):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1: Import
        self.create_import_tab()

        # Tab 2: Dashboard
        self.create_dashboard_tab()

        # Tab 3: Transactions
        self.create_transactions_tab()

        # Tab 4: Rules
        self.create_rules_tab()

        # Tab 5: Categories
        self.create_categories_tab()

        # Tab 6: Spending Plan (Conscious Spending)
        self.create_spending_plan_tab()

    def create_import_tab(self):
        """Create import tab"""
        import_frame = ttk.Frame(self.notebook)
        self.notebook.add(import_frame, text="📥 Import")

        # Instructions
        ttk.Label(
            import_frame,
            text="Import Transactions from CSV Files",
            font=('Arial', 16, 'bold')
        ).pack(pady=20)

        ttk.Label(
            import_frame,
            text="Select CSV files from your bank to import transactions",
            font=('Arial', 12)
        ).pack(pady=10)

        # Buttons frame
        btn_frame = ttk.Frame(import_frame)
        btn_frame.pack(pady=20)

        # Import buttons
        import_btn_frame = ttk.LabelFrame(btn_frame, text="Import & Process", padding=10)
        import_btn_frame.pack(side='left', padx=10)

        ttk.Button(
            import_btn_frame,
            text="📁 Select CSV Files",
            command=self.import_csv,
            width=30
        ).pack(pady=5)

        ttk.Button(
            import_btn_frame,
            text="🤖 Auto-Categorize",
            command=self.auto_categorize_all,
            width=30
        ).pack(pady=5)

        ttk.Button(
            import_btn_frame,
            text="🏷️ Classify Types",
            command=self.classify_types,
            width=30
        ).pack(pady=5)

        # Cleanup buttons
        cleanup_btn_frame = ttk.LabelFrame(btn_frame, text="Cleanup Tools", padding=10)
        cleanup_btn_frame.pack(side='left', padx=10)

        ttk.Button(
            cleanup_btn_frame,
            text="🔀 Merge Categories",
            command=self.merge_categories,
            width=30
        ).pack(pady=5)

        ttk.Button(
            cleanup_btn_frame,
            text="🔧 Fix Duplicates",
            command=self.fix_duplicate_categories,
            width=30
        ).pack(pady=5)

        ttk.Button(
            cleanup_btn_frame,
            text="🔍 Find Duplicate Txns",
            command=self.find_duplicates,
            width=30
        ).pack(pady=5)

        ttk.Button(
            cleanup_btn_frame,
            text="📋 View Category Mappings",
            command=self.view_mappings,
            width=30
        ).pack(pady=5)

        ttk.Button(
            cleanup_btn_frame,
            text="💳 Fix CC Payments",
            command=self.fix_cc_payments,
            width=30
        ).pack(pady=5)

        ttk.Button(
            cleanup_btn_frame,
            text="💵 Fix ATM Withdrawals",
            command=self.fix_atm_withdrawals,
            width=30
        ).pack(pady=5)

        # Results area
        ttk.Label(import_frame, text="Import Results:", font=('Arial', 12, 'bold')).pack(pady=10)

        self.import_results = scrolledtext.ScrolledText(
            import_frame,
            height=15,
            width=80,
            font=('Courier', 10)
        )
        self.import_results.pack(pady=10, padx=20, fill='both', expand=True)

    def create_dashboard_tab(self):
        """Create dashboard overview tab"""
        dash_frame = ttk.Frame(self.notebook)
        self.notebook.add(dash_frame, text="📊 Dashboard")

        # Title
        ttk.Label(
            dash_frame,
            text="Financial Dashboard",
            font=('Arial', 16, 'bold')
        ).pack(pady=10)

        # Date range controls
        control_frame = ttk.Frame(dash_frame)
        control_frame.pack(fill='x', padx=20, pady=5)

        ttk.Label(control_frame, text="Date Range:", font=('Arial', 10, 'bold')).pack(side='left', padx=5)

        self.dash_date_from_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.dash_date_from_var, width=12).pack(side='left', padx=2)
        ttk.Label(control_frame, text="to").pack(side='left', padx=5)
        self.dash_date_to_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.dash_date_to_var, width=12).pack(side='left', padx=2)

        ttk.Button(control_frame, text="This Month", command=self.set_dash_this_month, width=10).pack(side='left',
                                                                                                      padx=2)
        ttk.Button(control_frame, text="This Year", command=self.set_dash_this_year, width=10).pack(side='left', padx=2)
        ttk.Button(control_frame, text="All Time", command=self.set_dash_all_time, width=10).pack(side='left', padx=2)
        ttk.Button(control_frame, text="Refresh", command=self.refresh_dashboard, width=10).pack(side='left', padx=5)

        # Separator
        ttk.Separator(control_frame, orient='vertical').pack(side='left', fill='y', padx=10)

        # Browser dashboard button
        ttk.Button(
            control_frame,
            text="🌐 Open in Browser",
            command=self.launch_browser_dashboard,
            width=18
        ).pack(side='left', padx=5)

        # Summary metrics frame
        metrics_frame = ttk.LabelFrame(dash_frame, text="Summary Metrics", padding=10)
        metrics_frame.pack(fill='x', padx=20, pady=10)

        # Create 4 metric boxes
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill='x')

        # Income metric
        income_box = ttk.Frame(metrics_grid, relief='solid', borderwidth=1)
        income_box.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
        ttk.Label(income_box, text="💰 Income", font=('Arial', 10, 'bold')).pack(pady=5)
        self.income_label = ttk.Label(income_box, text="$0.00", font=('Arial', 18, 'bold'), foreground='green')
        self.income_label.pack(pady=5)

        # Expenses metric
        expense_box = ttk.Frame(metrics_grid, relief='solid', borderwidth=1)
        expense_box.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        ttk.Label(expense_box, text="💸 Expenses", font=('Arial', 10, 'bold')).pack(pady=5)
        self.expense_label = ttk.Label(expense_box, text="$0.00", font=('Arial', 18, 'bold'), foreground='red')
        self.expense_label.pack(pady=5)

        # Net metric
        net_box = ttk.Frame(metrics_grid, relief='solid', borderwidth=1)
        net_box.grid(row=0, column=2, padx=10, pady=5, sticky='ew')
        ttk.Label(net_box, text="📈 Net", font=('Arial', 10, 'bold')).pack(pady=5)
        self.net_label = ttk.Label(net_box, text="$0.00", font=('Arial', 18, 'bold'))
        self.net_label.pack(pady=5)

        # Transactions metric
        txn_box = ttk.Frame(metrics_grid, relief='solid', borderwidth=1)
        txn_box.grid(row=0, column=3, padx=10, pady=5, sticky='ew')
        ttk.Label(txn_box, text="📝 Transactions", font=('Arial', 10, 'bold')).pack(pady=5)
        self.txn_count_label = ttk.Label(txn_box, text="0", font=('Arial', 18, 'bold'))
        self.txn_count_label.pack(pady=5)

        # Make columns equal width
        for i in range(4):
            metrics_grid.columnconfigure(i, weight=1)

        # Monthly trends chart
        trends_frame = ttk.LabelFrame(dash_frame, text="Monthly Trends", padding=10)
        trends_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.trends_canvas = tk.Canvas(trends_frame, height=300, bg='white')
        self.trends_canvas.pack(fill='both', expand=True)

        # Category trends over time
        cat_trends_frame = ttk.LabelFrame(dash_frame, text="Expense Trends by Category (Top 5)", padding=10)
        cat_trends_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.cat_trends_canvas = tk.Canvas(cat_trends_frame, height=250, bg='white')
        self.cat_trends_canvas.pack(fill='both', expand=True)

        # Top categories
        top_cat_frame = ttk.LabelFrame(dash_frame, text="Top 5 Spending Categories", padding=10)
        top_cat_frame.pack(fill='x', padx=20, pady=10)

        self.top_categories_text = tk.Text(top_cat_frame, height=6, font=('Courier', 10))
        self.top_categories_text.pack(fill='x')

        # Initialize with current month
        self.set_dash_this_month()

    def set_dash_this_month(self):
        """Set dashboard to current month"""
        from datetime import datetime
        today = datetime.now()
        self.dash_date_from_var.set(f"{today.year}-{today.month:02d}-01")
        self.dash_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_dashboard()

    def set_dash_this_year(self):
        """Set dashboard to current year"""
        from datetime import datetime
        today = datetime.now()
        self.dash_date_from_var.set(f"{today.year}-01-01")
        self.dash_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_dashboard()

    def set_dash_all_time(self):
        """Clear dashboard date filters"""
        self.dash_date_from_var.set("")
        self.dash_date_to_var.set("")
        self.refresh_dashboard()

    def launch_browser_dashboard(self):
        """Launch Streamlit dashboard in browser"""
        import subprocess
        import webbrowser
        import time
        from pathlib import Path

        # Check if dashboard.py exists
        dashboard_path = Path("dashboard.py")
        if not dashboard_path.exists():
            messagebox.showerror(
                "Dashboard Not Found",
                "dashboard.py not found in the project directory.\n\n" +
                "Make sure the Streamlit dashboard file exists."
            )
            return

        # Show info dialog
        msg = "Launching Streamlit dashboard in your browser...\n\n"
        msg += "The dashboard will open at: http://localhost:8501\n\n"
        msg += "To stop the dashboard:\n"
        msg += "1. Close the browser tab\n"
        msg += "2. Press Ctrl+C in the terminal (if visible)\n"
        msg += "3. Or restart this app\n\n"
        msg += "Continue?"

        if not messagebox.askyesno("Launch Browser Dashboard", msg):
            return

        try:
            # Launch Streamlit in background
            # Use subprocess.Popen to run in background
            subprocess.Popen(
                ["streamlit", "run", "dashboard.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait a moment for server to start
            time.sleep(2)

            # Open browser
            webbrowser.open("http://localhost:8501")

            self.status_var.set("Browser dashboard launched at http://localhost:8501")

        except FileNotFoundError:
            messagebox.showerror(
                "Streamlit Not Found",
                "Streamlit is not installed.\n\n" +
                "Install it with:\n" +
                "pip install streamlit --break-system-packages"
            )
        except Exception as e:
            messagebox.showerror(
                "Launch Error",
                f"Failed to launch dashboard:\n\n{str(e)}"
            )

    def refresh_dashboard(self):
        """Refresh dashboard metrics and charts"""
        date_from = self.dash_date_from_var.get()
        date_to = self.dash_date_to_var.get()

        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Build date filter
        date_filter = ""
        params = []
        if date_from:
            date_filter += " AND date >= ?"
            params.append(date_from)
        if date_to:
            date_filter += " AND date <= ?"
            params.append(date_to)

        # Get summary metrics
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 AND (transaction_type = 'expense' OR transaction_type IS NULL) 
                    AND category NOT IN ('Credit Card Payment', 'Transfer') THEN ABS(amount) ELSE 0 END) as expenses,
                COUNT(*) as txn_count
            FROM transactions
            WHERE 1=1 {date_filter}
        """, params)

        metrics = cursor.fetchone()
        income = metrics['income'] or 0
        expenses = metrics['expenses'] or 0
        net = income - expenses
        txn_count = metrics['txn_count'] or 0

        # Update metric labels
        self.income_label.config(text=f"${income:,.2f}")
        self.expense_label.config(text=f"${expenses:,.2f}")
        self.net_label.config(text=f"${net:,.2f}")
        self.net_label.config(foreground='green' if net >= 0 else 'red')
        self.txn_count_label.config(text=f"{txn_count:,}")

        # Get monthly trends data
        cursor.execute(f"""
            SELECT 
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN amount < 0 AND (transaction_type = 'expense' OR transaction_type IS NULL)
                    AND category NOT IN ('Credit Card Payment', 'Transfer') THEN ABS(amount) ELSE 0 END) as expenses
            FROM transactions
            WHERE 1=1 {date_filter}
            GROUP BY month
            ORDER BY month
        """, params)

        monthly_data = cursor.fetchall()

        # Draw trends chart
        self.draw_monthly_trends(monthly_data)

        # Get top 5 categories for trends
        cursor.execute(f"""
            SELECT 
                category,
                SUM(ABS(amount)) as total
            FROM transactions
            WHERE amount < 0
              AND (transaction_type = 'expense' OR transaction_type IS NULL)
              AND category NOT IN ('Credit Card Payment', 'Transfer')
              {date_filter}
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        """, params)

        top_5_cats = [row['category'] for row in cursor.fetchall()]

        # Get category trends over time for top 5
        if top_5_cats:
            placeholders = ','.join(['?' for _ in top_5_cats])
            trend_params = params + top_5_cats

            cursor.execute(f"""
                SELECT 
                    strftime('%Y-%m', date) as month,
                    category,
                    SUM(ABS(amount)) as total
                FROM transactions
                WHERE amount < 0
                  AND (transaction_type = 'expense' OR transaction_type IS NULL)
                  AND category NOT IN ('Credit Card Payment', 'Transfer')
                  AND category IN ({placeholders})
                  {date_filter}
                GROUP BY month, category
                ORDER BY month, total DESC
            """, trend_params)

            category_trends = cursor.fetchall()
        else:
            category_trends = []

        # Draw category trends
        self.draw_category_trends(category_trends, top_5_cats)

        # Get top 5 categories summary
        cursor.execute(f"""
            SELECT 
                category,
                SUM(ABS(amount)) as total,
                COUNT(*) as count
            FROM transactions
            WHERE amount < 0
              AND (transaction_type = 'expense' OR transaction_type IS NULL)
              AND category NOT IN ('Credit Card Payment', 'Transfer')
              {date_filter}
            GROUP BY category
            ORDER BY total DESC
            LIMIT 5
        """, params)

        top_categories = cursor.fetchall()

        # Update top categories text
        self.top_categories_text.delete('1.0', 'end')
        total_top = sum(cat['total'] for cat in top_categories)

        for i, cat in enumerate(top_categories, 1):
            percent = (cat['total'] / total_top * 100) if total_top > 0 else 0
            line = f"{i}. {cat['category']:<25} ${cat['total']:>10,.2f}  ({percent:>5.1f}%)  {cat['count']:>3} txns\n"
            self.top_categories_text.insert('end', line)

    def draw_monthly_trends(self, data):
        """Draw monthly trends chart"""
        self.trends_canvas.delete('all')

        if not data:
            self.trends_canvas.create_text(
                400, 150,
                text="No data for selected period",
                font=('Arial', 12),
                fill='black'
            )
            return

        # Get canvas dimensions
        canvas_width = self.trends_canvas.winfo_width()
        canvas_height = 300

        if canvas_width < 100:
            canvas_width = 800

        # Margins
        margin_left = 80
        margin_right = 40
        margin_top = 40
        margin_bottom = 60

        chart_width = canvas_width - margin_left - margin_right
        chart_height = canvas_height - margin_top - margin_bottom

        # Find max value for scaling
        max_val = max(max(d['income'], d['expenses']) for d in data)
        if max_val == 0:
            max_val = 1

        # Calculate bar width
        bar_width = chart_width / (len(data) * 2.5)
        spacing = bar_width * 0.5

        # Draw axes
        # Y-axis
        self.trends_canvas.create_line(
            margin_left, margin_top,
            margin_left, margin_top + chart_height,
            width=2,
            fill='black'
        )

        # X-axis
        self.trends_canvas.create_line(
            margin_left, margin_top + chart_height,
                         margin_left + chart_width, margin_top + chart_height,
            width=2,
            fill='black'
        )

        # Y-axis labels
        for i in range(5):
            y = margin_top + chart_height - (i * chart_height / 4)
            val = max_val * i / 4

            self.trends_canvas.create_text(
                margin_left - 10,
                y,
                text=f"${val:,.0f}",
                anchor='e',
                font=('Arial', 9),
                fill='black'
            )

            # Grid line
            self.trends_canvas.create_line(
                margin_left, y,
                margin_left + chart_width, y,
                fill='lightgray',
                dash=(2, 2)
            )

        # Draw bars
        x = margin_left + spacing

        for i, month_data in enumerate(data):
            # Income bar (green)
            income_height = (month_data['income'] / max_val) * chart_height if max_val > 0 else 0
            self.trends_canvas.create_rectangle(
                x,
                margin_top + chart_height - income_height,
                x + bar_width,
                margin_top + chart_height,
                fill='#4ECDC4',
                outline=''
            )

            # Expenses bar (red)
            expense_height = (month_data['expenses'] / max_val) * chart_height if max_val > 0 else 0
            self.trends_canvas.create_rectangle(
                x + bar_width + spacing / 2,
                margin_top + chart_height - expense_height,
                x + bar_width * 2 + spacing / 2,
                margin_top + chart_height,
                fill='#FF6B6B',
                outline=''
            )

            # Month label
            from datetime import datetime
            try:
                month_obj = datetime.strptime(month_data['month'], '%Y-%m')
                month_label = month_obj.strftime('%b\n%Y')
            except:
                month_label = month_data['month']

            self.trends_canvas.create_text(
                x + bar_width + spacing / 4,
                margin_top + chart_height + 10,
                text=month_label,
                font=('Arial', 8),
                anchor='n',
                fill='black'
            )

            x += (bar_width * 2) + spacing * 2

        # Legend
        legend_x = margin_left + 20
        legend_y = margin_top - 20

        self.trends_canvas.create_rectangle(
            legend_x, legend_y,
            legend_x + 15, legend_y + 10,
            fill='#4ECDC4',
            outline=''
        )
        self.trends_canvas.create_text(
            legend_x + 20, legend_y + 5,
            text='Income',
            anchor='w',
            font=('Arial', 9),
            fill='black'
        )

        self.trends_canvas.create_rectangle(
            legend_x + 80, legend_y,
            legend_x + 95, legend_y + 10,
            fill='#FF6B6B',
            outline=''
        )
        self.trends_canvas.create_text(
            legend_x + 100, legend_y + 5,
            text='Expenses',
            anchor='w',
            font=('Arial', 9),
            fill='black'
        )

    def draw_category_trends(self, data, categories):
        """Draw category expense trends over time"""
        self.cat_trends_canvas.delete('all')

        if not data or not categories:
            self.cat_trends_canvas.create_text(
                400, 125,
                text="No category data for selected period",
                font=('Arial', 12),
                fill='black'
            )
            return

        # Organize data by month
        months = {}
        for row in data:
            month = row['month']
            if month not in months:
                months[month] = {}
            months[month][row['category']] = row['total']

        if not months:
            return

        # Get canvas dimensions
        canvas_width = self.cat_trends_canvas.winfo_width()
        canvas_height = 250

        if canvas_width < 100:
            canvas_width = 800

        # Margins
        margin_left = 80
        margin_right = 150
        margin_top = 40
        margin_bottom = 40

        chart_width = canvas_width - margin_left - margin_right
        chart_height = canvas_height - margin_top - margin_bottom

        # Sort months
        sorted_months = sorted(months.keys())

        # Find max value
        max_val = max(
            sum(months[m].values()) for m in sorted_months
        )
        if max_val == 0:
            max_val = 1

        # Colors for categories
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

        # Draw axes
        self.cat_trends_canvas.create_line(
            margin_left, margin_top,
            margin_left, margin_top + chart_height,
            width=2,
            fill='black'
        )

        self.cat_trends_canvas.create_line(
            margin_left, margin_top + chart_height,
                         margin_left + chart_width, margin_top + chart_height,
            width=2,
            fill='black'
        )

        # Y-axis labels
        for i in range(5):
            y = margin_top + chart_height - (i * chart_height / 4)
            val = max_val * i / 4

            self.cat_trends_canvas.create_text(
                margin_left - 10,
                y,
                text=f"${val:,.0f}",
                anchor='e',
                font=('Arial', 9),
                fill='black'
            )

            # Grid line
            self.cat_trends_canvas.create_line(
                margin_left, y,
                margin_left + chart_width, y,
                fill='lightgray',
                dash=(2, 2)
            )

        # Calculate positions
        x_step = chart_width / (len(sorted_months) - 1) if len(sorted_months) > 1 else chart_width

        # Draw lines for each category
        for cat_idx, category in enumerate(categories):
            color = colors[cat_idx % len(colors)]
            points = []

            for month_idx, month in enumerate(sorted_months):
                amount = months[month].get(category, 0)

                x = margin_left + (month_idx * x_step)
                y = margin_top + chart_height - (amount / max_val * chart_height)

                points.append((x, y))

            # Draw line
            if len(points) > 1:
                for i in range(len(points) - 1):
                    self.cat_trends_canvas.create_line(
                        points[i][0], points[i][1],
                        points[i + 1][0], points[i + 1][1],
                        fill=color,
                        width=2
                    )

            # Draw points
            for x, y in points:
                self.cat_trends_canvas.create_oval(
                    x - 3, y - 3,
                    x + 3, y + 3,
                    fill=color,
                    outline='white'
                )

        # X-axis labels (months)
        from datetime import datetime
        for month_idx, month in enumerate(sorted_months):
            x = margin_left + (month_idx * x_step)

            try:
                month_obj = datetime.strptime(month, '%Y-%m')
                month_label = month_obj.strftime('%b\n%y')
            except:
                month_label = month

            self.cat_trends_canvas.create_text(
                x,
                margin_top + chart_height + 10,
                text=month_label,
                font=('Arial', 8),
                anchor='n',
                fill='black'
            )

        # Legend
        legend_x = canvas_width - margin_right + 10
        legend_y = margin_top

        for cat_idx, category in enumerate(categories):
            color = colors[cat_idx % len(colors)]
            y = legend_y + (cat_idx * 20)

            # Color box
            self.cat_trends_canvas.create_rectangle(
                legend_x, y,
                legend_x + 15, y + 10,
                fill=color,
                outline=''
            )

            # Category name
            cat_name = category[:15] if len(category) > 15 else category
            self.cat_trends_canvas.create_text(
                legend_x + 20, y + 5,
                text=cat_name,
                anchor='w',
                font=('Arial', 8),
                fill='black'
            )

    def create_transactions_tab(self):
        """Create transactions tab"""
        txn_frame = ttk.Frame(self.notebook)
        self.notebook.add(txn_frame, text="💰 Transactions")

        # Top controls — row 1: date range
        row1 = ttk.Frame(txn_frame)
        row1.pack(fill='x', padx=5, pady=(5, 2))

        date_frame = ttk.LabelFrame(row1, text="Date Range", padding=5)
        date_frame.pack(side='left', padx=5)

        ttk.Label(date_frame, text="From:").pack(side='left', padx=2)
        self.date_from_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_from_var, width=12).pack(side='left', padx=2)

        ttk.Label(date_frame, text="To:").pack(side='left', padx=2)
        self.date_to_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_to_var, width=12).pack(side='left', padx=2)

        quick_frame = ttk.Frame(date_frame)
        quick_frame.pack(side='left', padx=5)
        ttk.Button(quick_frame, text="This Month", command=self.set_this_month, width=10).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="Last Month", command=self.set_last_month, width=10).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="This Year",  command=self.set_this_year,  width=10).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="All Time",   command=self.set_all_time,   width=10).pack(side='left', padx=2)

        # Row 2: account filter + search + show limit
        row2 = ttk.Frame(txn_frame)
        row2.pack(fill='x', padx=5, pady=(0, 5))

        ttk.Label(row2, text="Account:").pack(side='left', padx=5)
        self.account_filter_var = tk.StringVar(value="All Accounts")
        self.account_combo = ttk.Combobox(
            row2,
            textvariable=self.account_filter_var,
            values=["All Accounts"],
            width=24,
            state='readonly'
        )
        self.account_combo.pack(side='left', padx=5)
        self.account_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_transactions())

        ttk.Label(row2, text="Filter:").pack(side='left', padx=5)
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(row2, textvariable=self.filter_var, width=28)
        filter_entry.pack(side='left', padx=5)
        filter_entry.bind('<KeyRelease>', lambda e: self.refresh_transactions())

        ttk.Button(row2, text="Refresh", command=self.refresh_transactions).pack(side='left', padx=5)

        ttk.Label(row2, text="Show:").pack(side='left', padx=5)
        self.limit_var = tk.StringVar(value="All")
        limit_combo = ttk.Combobox(
            row2,
            textvariable=self.limit_var,
            values=["50", "100", "200", "500", "All"],
            width=8
        )
        limit_combo.pack(side='left', padx=5)
        limit_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_transactions())

        # Transactions tree
        tree_frame = ttk.Frame(txn_frame)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.txn_tree = ttk.Treeview(
            tree_frame,
            columns=('date', 'description', 'amount', 'category', 'account', 'type'),
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=self.txn_tree.yview)
        hsb.config(command=self.txn_tree.xview)

        # Layout
        self.txn_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Configure columns
        self.txn_tree.heading('#0', text='ID')
        self.txn_tree.heading('date', text='Date')
        self.txn_tree.heading('description', text='Description')
        self.txn_tree.heading('amount', text='Amount')
        self.txn_tree.heading('category', text='Category')
        self.txn_tree.heading('account', text='Account')
        self.txn_tree.heading('type', text='Type')

        self.txn_tree.column('#0', width=50)
        self.txn_tree.column('date', width=100)
        self.txn_tree.column('description', width=300)
        self.txn_tree.column('amount', width=100)
        self.txn_tree.column('category', width=150)
        self.txn_tree.column('account', width=150)
        self.txn_tree.column('type', width=80)

        # Double-click to edit
        self.txn_tree.bind('<Double-1>', self.edit_transaction)

        # Bottom buttons
        btn_frame = ttk.Frame(txn_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="➕ Add Transaction",
            command=self.add_transaction
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="✏️ Edit Selected",
            command=lambda: self.edit_transaction(None)
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ Delete Selected",
            command=self.delete_transaction
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="📊 Export CSV",
            command=self.export_transactions_csv
        ).pack(side='right', padx=5)

    def export_transactions_csv(self):
        """Export the current filtered transaction view to a CSV file."""
        import csv
        from datetime import datetime
        from tkinter import filedialog

        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        filter_text = self.filter_var.get()

        query = """SELECT id, date, description, amount, category, account_name,
                          transaction_type, tags, notes
                   FROM transactions WHERE 1=1"""
        params = []
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)
        if filter_text:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([f"%{filter_text}%", f"%{filter_text}%"])
        query += " ORDER BY date DESC"

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            messagebox.showinfo("No Data", "No transactions match the current filter.")
            return

        default_name = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name
        )
        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Date', 'Description', 'Amount', 'Category',
                                 'Account', 'Type', 'Tags', 'Notes'])
                for row in rows:
                    writer.writerow([
                        row['id'], row['date'], row['description'],
                        row['amount'], row['category'], row['account_name'],
                        row['transaction_type'] or '', row['tags'] or '', row['notes'] or ''
                    ])
            messagebox.showinfo("Export Complete",
                                f"Exported {len(rows)} transactions to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")

    def create_rules_tab(self):
        """Create rules management tab"""
        rules_frame = ttk.Frame(self.notebook)
        self.notebook.add(rules_frame, text="📋 Rules")

        # Split into two panes
        paned = ttk.PanedWindow(rules_frame, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left: Rules list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Categorization Rules", font=('Arial', 12, 'bold')).pack(pady=5)

        # Rules tree
        self.rules_tree = ttk.Treeview(
            left_frame,
            columns=('keywords', 'count'),
            show='tree headings'
        )

        self.rules_tree.heading('#0', text='Category')
        self.rules_tree.heading('keywords', text='Keywords')
        self.rules_tree.heading('count', text='Count')

        self.rules_tree.column('#0', width=150)
        self.rules_tree.column('keywords', width=300)
        self.rules_tree.column('count', width=80)

        self.rules_tree.pack(fill='both', expand=True, pady=5)

        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill='x', pady=5)

        ttk.Button(
            btn_frame,
            text="➕ Add Rule",
            command=self.add_rule
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="✏️ Edit Rule",
            command=self.edit_rule
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ Delete Rule",
            command=self.delete_rule
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="🔄 Refresh",
            command=self.refresh_rules
        ).pack(side='left', padx=5)

        # Right: Rule details
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Add New Rule", font=('Arial', 12, 'bold')).pack(pady=10)

        # Form
        form_frame = ttk.Frame(right_frame)
        form_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(form_frame, text="Category:").grid(row=0, column=0, sticky='w', pady=5)
        self.rule_category_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.rule_category_var, width=30).grid(row=0, column=1, pady=5)

        ttk.Label(form_frame, text="Keyword:").grid(row=1, column=0, sticky='w', pady=5)
        self.rule_keyword_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.rule_keyword_var, width=30).grid(row=1, column=1, pady=5)

        ttk.Button(
            form_frame,
            text="💾 Save Rule",
            command=self.save_rule
        ).grid(row=2, column=0, columnspan=2, pady=20)

        # Load rules
        self.refresh_rules()

    def create_categories_tab(self):
        """Create categories tab"""
        cat_frame = ttk.Frame(self.notebook)
        self.notebook.add(cat_frame, text="🏷️ Categories")

        # Top controls with date range
        control_frame = ttk.Frame(cat_frame)
        control_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(
            control_frame,
            text="Spending by Category",
            font=('Arial', 14, 'bold')
        ).pack(side='left', padx=10)

        # Date range
        date_frame = ttk.LabelFrame(control_frame, text="Date Range", padding=5)
        date_frame.pack(side='right', padx=10)

        ttk.Label(date_frame, text="From:").pack(side='left', padx=2)
        self.cat_date_from_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.cat_date_from_var, width=12).pack(side='left', padx=2)

        ttk.Label(date_frame, text="To:").pack(side='left', padx=2)
        self.cat_date_to_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.cat_date_to_var, width=12).pack(side='left', padx=2)

        # Quick buttons
        ttk.Button(date_frame, text="This Month", command=self.set_cat_this_month, width=10).pack(side='left', padx=2)
        ttk.Button(date_frame, text="Last Month", command=self.set_cat_last_month, width=10).pack(side='left', padx=2)
        ttk.Button(date_frame, text="This Year", command=self.set_cat_this_year, width=10).pack(side='left', padx=2)
        ttk.Button(date_frame, text="All Time", command=self.set_cat_all_time, width=10).pack(side='left', padx=2)

        # Categories tree
        self.cat_tree = ttk.Treeview(
            cat_frame,
            columns=('count', 'total', 'income', 'net', 'percent'),
            show='tree headings'
        )

        self.cat_tree.heading('#0', text='Category')
        self.cat_tree.heading('count', text='Transactions')
        self.cat_tree.heading('total', text='Expenses')
        self.cat_tree.heading('income', text='Income')
        self.cat_tree.heading('net', text='Net')
        self.cat_tree.heading('percent', text='Percentage')

        self.cat_tree.column('#0', width=200)
        self.cat_tree.column('count', width=120)
        self.cat_tree.column('total', width=120)
        self.cat_tree.column('income', width=120)
        self.cat_tree.column('net', width=120)
        self.cat_tree.column('percent', width=100)

        self.cat_tree.pack(fill='both', expand=True, padx=20, pady=10)

        # Bind double-click to show transactions
        self.cat_tree.bind('<Double-1>', self.show_category_transactions)

        # Bind right-click for context menu
        self.cat_tree.bind('<Button-2>', self.show_category_menu)  # Mac right-click
        self.cat_tree.bind('<Button-3>', self.show_category_menu)  # Windows/Linux right-click

        # Add instruction label
        ttk.Label(
            cat_frame,
            text="💡 Tip: Double-click a category to view ALL transactions (all time)",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        ).pack(pady=5)

        # Chart area
        chart_frame = ttk.LabelFrame(cat_frame, text="Spending Distribution", padding=10)
        chart_frame.pack(fill='x', padx=20, pady=10)

        # Canvas for bar chart
        self.cat_chart_canvas = tk.Canvas(chart_frame, height=200, bg='white')
        self.cat_chart_canvas.pack(fill='both', expand=True)

        # Refresh button
        ttk.Button(
            cat_frame,
            text="🔄 Refresh",
            command=self.refresh_categories
        ).pack(pady=10)

        # Load categories
        self.refresh_categories()

    def create_status_bar(self):
        """Create status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief='sunken',
            anchor='w'
        )
        status_bar.pack(side='bottom', fill='x')

    # Import functions

    @staticmethod
    def _classify_transaction_type(description: str, amount: float, category: str) -> str:
        """Determine transaction type (expense/income/transfer) from description, amount, category."""
        import re

        TRANSFER_PATTERNS = [
            r'CHASE.*CREDIT.*AUTOPAY',
            r'CHASE.*PAYMENT',
            r'AMERICAN EXPRESS.*PMT',
            r'AMEX.*PAYMENT',
            r'PAYMENT.*THANK YOU',
            r'THANK YOU.*MOBILE',
            r'ONLINE PAYMENT.*THANK YOU',
            r'MOBILE PAYMENT.*THANK YOU',
            r'TRANSFER',
            r'ROBINHOOD',
            r'ZELLE',
            r'VENMO',
        ]

        if category in ('Credit Card Payment', 'Transfer', 'Investment'):
            return 'transfer'

        desc_upper = description.upper()
        for pattern in TRANSFER_PATTERNS:
            if re.search(pattern, desc_upper):
                return 'transfer'

        if amount > 0:
            return 'income'

        return 'expense'

    def import_csv(self):
        """Import CSV files"""
        files = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not files:
            return

        self.import_results.delete('1.0', 'end')
        self.import_results.insert('end', f"Importing {len(files)} file(s)...\n\n")

        total_imported = 0

        for file_path in files:
            file_path = Path(file_path)
            self.import_results.insert('end', f"Processing: {file_path.name}\n")

            # Detect parser
            parser = detect_parser(file_path)

            if not parser:
                self.import_results.insert('end', f"  ❌ Unknown format\n\n")
                continue

            try:
                # Derive a human-readable account name from the filename
                account_name = parser.get_account_name(file_path)

                # Parse
                transactions = parser.parse(file_path, account_name)

                # Get existing categories for mapping
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL")
                existing_categories = [row['category'] for row in cursor.fetchall()]

                # Convert to dicts and apply category mapping
                txn_dicts = []
                mapped_count = 0

                for txn in transactions:
                    original_category = txn.category
                    mapped_category = self.category_mapper.map_category(
                        txn.category,
                        existing_categories
                    )

                    if mapped_category != original_category:
                        mapped_count += 1

                    txn_type = self._classify_transaction_type(
                        txn.description, txn.amount, mapped_category
                    )
                    txn_dict = {
                        'date': txn.date.strftime('%Y-%m-%d') if hasattr(txn.date, 'strftime') else txn.date,
                        'description': txn.description,
                        'amount': txn.amount,
                        'account_name': txn.account_name,
                        'account_type': txn.account_type,
                        'institution': txn.institution,
                        'category': mapped_category,
                        'transaction_type': txn_type,
                        'notes': txn.notes,
                        'raw_data': txn.raw_data
                    }
                    txn_dicts.append(txn_dict)

                # Import
                result = self.db.add_transactions(txn_dicts)

                if isinstance(result, tuple):
                    imported, duplicates = result
                else:
                    imported = result
                    duplicates = 0

                total_imported += imported

                status_msg = f"  ✅ Imported: {imported}, Duplicates: {duplicates}"
                if mapped_count > 0:
                    status_msg += f", Mapped: {mapped_count}"

                self.import_results.insert('end', status_msg + "\n\n")

            except Exception as e:
                self.import_results.insert('end', f"  ❌ Error: {str(e)}\n\n")

        self.import_results.insert('end', f"\n{'=' * 60}\n")
        self.import_results.insert('end', f"Total imported: {total_imported} transactions\n")

        self.status_var.set(f"Imported {total_imported} transactions")
        self.refresh_transactions()

        messagebox.showinfo("Import Complete", f"Imported {total_imported} new transactions")

    def auto_categorize_all(self):
        """Auto-categorize all uncategorized transactions"""
        # Create dialog with three options
        dialog = tk.Toplevel(self.root)
        dialog.title("Auto-Categorize Options")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Auto-Categorize Transactions",
            font=('Arial', 14, 'bold')
        ).pack(pady=20)

        ttk.Label(
            dialog,
            text="What would you like to categorize?",
            font=('Arial', 11)
        ).pack(pady=10)

        result = {'choice': None}

        def choose_all():
            result['choice'] = 'all'
            dialog.destroy()

        def choose_uncategorized():
            result['choice'] = 'uncategorized'
            dialog.destroy()

        def choose_recent():
            result['choice'] = 'recent'
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame,
            text="📋 All Transactions\n(Re-categorize everything)",
            command=choose_all,
            width=30
        ).pack(pady=5)

        ttk.Button(
            btn_frame,
            text="❓ Uncategorized Only\n(Only 'Uncategorized')",
            command=choose_uncategorized,
            width=30
        ).pack(pady=5)

        ttk.Button(
            btn_frame,
            text="🆕 Recent Imports\n(Last 30 days - for new transactions)",
            command=choose_recent,
            width=30
        ).pack(pady=5)

        ttk.Button(
            btn_frame,
            text="Cancel",
            command=cancel,
            width=30
        ).pack(pady=10)

        # Wait for dialog
        self.root.wait_window(dialog)

        if not result['choice']:
            return

        self.status_var.set("Auto-categorizing...")

        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Build query based on choice
        if result['choice'] == 'all':
            # Re-categorize ALL transactions
            cursor.execute("""
                SELECT id, description, category
                FROM transactions
            """)
            overwrite = True
        elif result['choice'] == 'uncategorized':
            # Only uncategorized
            cursor.execute("""
                SELECT id, description, category
                FROM transactions
                WHERE category = 'Uncategorized'
            """)
            overwrite = False
        else:  # recent
            # Last 30 days only
            from datetime import datetime, timedelta
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT id, description, category
                FROM transactions
                WHERE date >= ?
            """, (thirty_days_ago,))
            overwrite = False

        remaining = cursor.fetchall()

        if not remaining:
            messagebox.showinfo("No Transactions", "No transactions found to categorize.")
            return

        learned_count = 0

        for txn in remaining:
            new_cat = self.learned_rules.categorize(txn['description'])
            if new_cat != 'Uncategorized' and (overwrite or txn['category'] == 'Uncategorized'):
                cursor.execute(
                    "UPDATE transactions SET category = ? WHERE id = ?",
                    (new_cat, txn['id'])
                )
                learned_count += 1

        conn.commit()

        # Also try built-in rules
        stats = Categorizer.categorize_all(self.db, overwrite_existing=overwrite)
        total = stats['updated'] + learned_count

        # Show results
        choice_text = {
            'all': 'all transactions',
            'uncategorized': 'uncategorized transactions',
            'recent': 'recent transactions (last 30 days)'
        }

        self.status_var.set(f"Categorized {total} transactions")
        self.refresh_transactions()
        self.refresh_categories()

        messagebox.showinfo(
            "Auto-Categorize Complete",
            f"Checked {len(remaining)} {choice_text[result['choice']]}\n\n"
            f"Categorized {total} transactions:\n"
            f"• Learned rules: {learned_count}\n"
            f"• Built-in rules: {stats['updated']}"
        )

    def classify_types(self):
        """Classify transaction types"""
        # Implementation from classify_transaction_types.py
        import re

        TRANSFER_PATTERNS = [
            r'CHASE.*CREDIT.*AUTOPAY',
            r'CHASE.*PAYMENT',
            r'AMERICAN EXPRESS.*PMT',
            r'AMEX.*PAYMENT',
            r'ONLINE PAYMENT.*THANK YOU',
            r'MOBILE PAYMENT.*THANK YOU',
            r'TRANSFER',
            r'ROBINHOOD',
            r'ZELLE',
            r'VENMO',
        ]

        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, description, amount, category
            FROM transactions
            WHERE transaction_type IS NULL
        """)

        transactions = cursor.fetchall()
        classified = 0

        for txn in transactions:
            desc_upper = txn['description'].upper()

            is_transfer = False
            for pattern in TRANSFER_PATTERNS:
                if re.search(pattern, desc_upper):
                    is_transfer = True
                    break

            if txn['category'] in ['Credit Card Payment', 'Transfer', 'Investment']:
                is_transfer = True

            if is_transfer:
                txn_type = 'transfer'
            elif txn['amount'] > 0:
                txn_type = 'income'
            else:
                txn_type = 'expense'

            cursor.execute(
                "UPDATE transactions SET transaction_type = ? WHERE id = ?",
                (txn_type, txn['id'])
            )
            classified += 1

        conn.commit()

        self.status_var.set(f"Classified {classified} transactions")
        self.refresh_transactions()

        messagebox.showinfo("Classification Complete", f"Classified {classified} transactions")

    def find_duplicates(self):
        """Find duplicate transactions"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Method 1: Exact duplicates (same date, description, amount, account)
        cursor.execute("""
            SELECT date, description, amount, account_name, COUNT(*) as count
            FROM transactions
            GROUP BY date, description, amount, account_name
            HAVING count > 1
        """)

        exact_duplicates = cursor.fetchall()

        # Method 2: Likely duplicates (same date, description, amount but different account name)
        # This catches CSV files imported with different account names
        cursor.execute("""
            SELECT date, description, amount, GROUP_CONCAT(DISTINCT account_name) as accounts, COUNT(*) as count
            FROM transactions
            GROUP BY date, description, amount
            HAVING count > 1
        """)

        likely_duplicates = cursor.fetchall()

        if not exact_duplicates and not likely_duplicates:
            messagebox.showinfo("No Duplicates", "No duplicate transactions found!")
            return

        # Show results
        msg = ""

        if exact_duplicates:
            msg += f"Found {len(exact_duplicates)} sets of EXACT duplicates:\n\n"
            for dup in exact_duplicates[:5]:
                msg += f"• {dup['date']} - {dup['description'][:40]} - ${dup['amount']} ({dup['count']} copies)\n"
            if len(exact_duplicates) > 5:
                msg += f"... and {len(exact_duplicates) - 5} more\n"

        if likely_duplicates:
            msg += f"\n\nFound {len(likely_duplicates)} sets of LIKELY duplicates:\n"
            msg += "(Same date/amount/description, different account names)\n\n"
            for dup in likely_duplicates[:5]:
                msg += f"• {dup['date']} - {dup['description'][:40]} - ${dup['amount']} ({dup['count']} copies)\n"
                msg += f"  Accounts: {dup['accounts']}\n"
            if len(likely_duplicates) > 5:
                msg += f"... and {len(likely_duplicates) - 5} more\n"

        msg += "\n\nWould you like to open a tool to review and delete duplicates?"

        if messagebox.askyesno("Duplicates Found", msg):
            DuplicateReviewDialog(self.root, self.db, self.refresh_transactions)

    def fix_duplicate_categories(self):
        """Fix categories that differ only in capitalization"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Get all unique categories (case-insensitive grouping)
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM transactions
            WHERE category IS NOT NULL
            GROUP BY LOWER(category)
            HAVING COUNT(DISTINCT category) > 1
        """)

        duplicates = cursor.fetchall()

        if not duplicates:
            messagebox.showinfo("No Duplicates", "No duplicate categories found!")
            return

        # For each duplicate group, find all variations
        fixes = []
        for dup in duplicates:
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM transactions
                WHERE LOWER(category) = LOWER(?)
                GROUP BY category
                ORDER BY count DESC
            """, (dup['category'],))

            variations = cursor.fetchall()

            # Most common variation becomes canonical
            canonical = variations[0]['category']

            for var in variations[1:]:
                fixes.append({
                    'from': var['category'],
                    'to': canonical,
                    'count': var['count']
                })

        if not fixes:
            messagebox.showinfo("No Duplicates", "No duplicate categories found!")
            return

        # Show what will be fixed
        msg = "Found duplicate categories with different capitalization:\n\n"
        for fix in fixes[:10]:
            msg += f"• '{fix['from']}' → '{fix['to']}' ({fix['count']} txns)\n"

        if len(fixes) > 10:
            msg += f"\n... and {len(fixes) - 10} more"

        msg += f"\n\nFix {sum(f['count'] for f in fixes)} transactions?"

        if messagebox.askyesno("Fix Duplicate Categories", msg):
            for fix in fixes:
                cursor.execute(
                    "UPDATE transactions SET category = ? WHERE category = ?",
                    (fix['to'], fix['from'])
                )

            conn.commit()

            self.refresh_transactions()
            self.refresh_categories()

            messagebox.showinfo(
                "Fixed!",
                f"Fixed {len(fixes)} duplicate categories affecting {sum(f['count'] for f in fixes)} transactions"
            )

    def merge_categories(self):
        """Open dialog to merge categories"""
        MergeCategoriesDialog(self.root, self.db, self.refresh_transactions, self.refresh_categories)

    def fix_account_names(self):
        """Rename existing file-stem account names to proper bank account names."""
        import re

        PATTERNS = [
            # Chase checking: Chase9707_Activity... → Chase Checking *9707
            (re.compile(r'^[Cc]hase(\d{4})_Activity', re.IGNORECASE),
             lambda m: f"Chase Checking *{m.group(1)}"),
            # Chase credit: Chase4370_... without Activity → Chase Credit *4370
            # (Chase credit files may also have Activity in name, so check both parsers)
            # We'll try checking first, then credit if no match (same regex, different label)
        ]

        def derive_name(old):
            import re
            # Chase checking pattern
            m = re.search(r'[Cc]hase(\d{4})_Activity', old)
            if m:
                return f"Chase Checking *{m.group(1)}"
            # Chase credit pattern (no "Activity" keyword, just Chase + 4 digits)
            m = re.search(r'[Cc]hase(\d{4})', old)
            if m:
                return f"Chase Credit *{m.group(1)}"
            # "activity..." prefix without bank → Discover
            if re.match(r'^activity', old, re.IGNORECASE):
                return "Discover"
            # BofA
            if re.search(r'(bank.?of.?america|bofa|boa)', old, re.IGNORECASE):
                m2 = re.search(r'(\d{4})', old)
                return f"Bank of America *{m2.group(1)}" if m2 else "Bank of America"
            # Amex
            if re.search(r'(amex|american.?express)', old, re.IGNORECASE):
                m2 = re.search(r'(\d+)', old)
                return f"Amex *{m2.group(1)[-5:]}" if m2 else "American Express"
            return None  # No change

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_name FROM transactions ORDER BY account_name")
        old_names = [row['account_name'] for row in cursor.fetchall()]

        updates = {}
        for old in old_names:
            new = derive_name(old)
            if new and new != old:
                updates[old] = new

        if not updates:
            messagebox.showinfo("Fix Account Names", "All account names already look correct.")
            return

        msg = "The following account names will be updated:\n\n"
        for old, new in updates.items():
            msg += f"  {old[:45]}  →  {new}\n"
        msg += f"\n{len(updates)} account name(s) will change."

        if not messagebox.askyesno("Fix Account Names?", msg):
            return

        for old, new in updates.items():
            cursor.execute(
                "UPDATE transactions SET account_name = ? WHERE account_name = ?",
                (new, old)
            )
        conn.commit()

        self.refresh_transactions()
        messagebox.showinfo("Done", f"Updated {len(updates)} account name(s).")

    def view_mappings(self):
        """View current category mappings"""
        mappings = self.category_mapper.get_all_mappings()
        auto_mappings = self.category_mapper.auto_learned_mappings

        msg = "Category Mappings (for future imports):\n\n"

        if mappings:
            msg += "Manual Mappings:\n"
            for from_cat, to_cat in sorted(mappings.items()):
                msg += f"  • '{from_cat}' → '{to_cat}'\n"
            msg += f"\nTotal: {len(mappings)} manual mappings\n"

        if auto_mappings:
            msg += "\nAuto-Learned Mappings:\n"
            for from_cat, to_cat in sorted(list(auto_mappings.items())[:20]):  # Show first 20
                msg += f"  • '{from_cat}' → '{to_cat}'\n"

            if len(auto_mappings) > 20:
                msg += f"\n... and {len(auto_mappings) - 20} more\n"

            msg += f"\nTotal: {len(auto_mappings)} auto-learned mappings\n"

        if not mappings and not auto_mappings:
            msg += "No mappings configured yet.\n\n"
            msg += "Mappings are created when you:\n"
            msg += "  • Merge categories\n"
            msg += "  • Import files (auto-learned)\n"

        messagebox.showinfo("Category Mappings", msg)

    def fix_cc_payments(self):
        """Mark all Credit Card Payment transactions as transfers"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Count how many CC payments are not marked as transfers
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM transactions
            WHERE category = 'Credit Card Payment'
              AND (transaction_type != 'transfer' OR transaction_type IS NULL)
        """)

        count = cursor.fetchone()['count']

        if count == 0:
            messagebox.showinfo(
                "Already Fixed",
                "All Credit Card Payment transactions are already marked as transfers!"
            )
            return

        msg = f"Found {count} Credit Card Payment transaction(s) that are not marked as transfers.\n\n"
        msg += "This will mark them as 'transfer' so they don't appear in spending totals.\n\n"
        msg += "Continue?"

        if messagebox.askyesno("Fix CC Payments", msg):
            cursor.execute("""
                UPDATE transactions
                SET transaction_type = 'transfer'
                WHERE category = 'Credit Card Payment'
                  AND (transaction_type != 'transfer' OR transaction_type IS NULL)
            """)

            conn.commit()

            self.refresh_transactions()
            self.refresh_categories()

            messagebox.showinfo(
                "Fixed!",
                f"Marked {count} Credit Card Payment transaction(s) as transfers.\n\n" +
                "They will no longer appear in spending totals!"
            )

    def fix_atm_withdrawals(self):
        """Review and fix ATM withdrawals that should be expenses"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Find ATM withdrawals marked as transfers
        cursor.execute("""
            SELECT id, date, description, amount, category, transaction_type
            FROM transactions
            WHERE (description LIKE '%ATM%' OR description LIKE '%WITHDRAWAL%')
              AND transaction_type = 'transfer'
            ORDER BY date DESC
        """)

        atm_txns = cursor.fetchall()

        if not atm_txns:
            messagebox.showinfo(
                "No ATM Withdrawals",
                "No ATM withdrawals marked as transfers found."
            )
            return

        # Show list for user to review
        msg = f"Found {len(atm_txns)} ATM withdrawal(s) marked as transfers:\n\n"

        for txn in atm_txns[:10]:
            msg += f"• {txn['date']} - {txn['description'][:40]} - ${abs(txn['amount']):.2f}\n"

        if len(atm_txns) > 10:
            msg += f"\n... and {len(atm_txns) - 10} more\n"

        msg += "\nATM withdrawals are usually expenses (cash for spending).\n"
        msg += "Only mark as 'transfer' if moving money between your own accounts.\n\n"
        msg += "Change all to 'expense'?"

        if messagebox.askyesno("Fix ATM Withdrawals", msg):
            cursor.execute("""
                UPDATE transactions
                SET transaction_type = 'expense'
                WHERE (description LIKE '%ATM%' OR description LIKE '%WITHDRAWAL%')
                  AND transaction_type = 'transfer'
            """)

            count = cursor.rowcount
            conn.commit()

            self.refresh_transactions()
            self.refresh_categories()

            messagebox.showinfo(
                "Fixed!",
                f"Changed {count} ATM withdrawal(s) to 'expense'.\n\n" +
                "They will now appear in spending totals."
            )
        else:
            messagebox.showinfo(
                "Manual Review",
                "You can manually edit individual transactions:\n\n" +
                "1. Go to Transactions tab\n" +
                "2. Filter for 'ATM' or 'WITHDRAWAL'\n" +
                "3. Double-click each transaction\n" +
                "4. Change Type to 'Expense' or 'Transfer' as needed"
            )

    # Transaction functions

    def set_this_month(self):
        """Set date range to current month"""
        from datetime import datetime
        today = datetime.now()
        self.date_from_var.set(f"{today.year}-{today.month:02d}-01")
        self.date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_transactions()

    def set_last_month(self):
        """Set date range to last month"""
        from datetime import datetime, timedelta
        import calendar

        today = datetime.now()

        # First day of current month
        first_this_month = datetime(today.year, today.month, 1)

        # Last day of last month
        last_day_last_month = first_this_month - timedelta(days=1)

        # First day of last month
        first_day_last_month = datetime(last_day_last_month.year, last_day_last_month.month, 1)

        self.date_from_var.set(first_day_last_month.strftime("%Y-%m-%d"))
        self.date_to_var.set(last_day_last_month.strftime("%Y-%m-%d"))
        self.refresh_transactions()

    def set_this_year(self):
        """Set date range to current year"""
        from datetime import datetime
        today = datetime.now()
        self.date_from_var.set(f"{today.year}-01-01")
        self.date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_transactions()

    def set_all_time(self):
        """Clear date range to show all time"""
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.refresh_transactions()

    # ─── Spending Plan (Conscious Spending) tab ────────────────────────────────

    def create_spending_plan_tab(self):
        """Create the Conscious Spending Plan tab."""
        from datetime import datetime

        plan_frame = ttk.Frame(self.notebook)
        self.notebook.add(plan_frame, text="💡 Spending Plan")

        # ── Top controls ──────────────────────────────────────────────────────
        ctrl = ttk.Frame(plan_frame)
        ctrl.pack(fill='x', padx=5, pady=5)

        date_lf = ttk.LabelFrame(ctrl, text="Date Range", padding=5)
        date_lf.pack(side='left', padx=5)

        ttk.Label(date_lf, text="From:").pack(side='left', padx=2)
        self.sp_date_from_var = tk.StringVar()
        ttk.Entry(date_lf, textvariable=self.sp_date_from_var, width=12).pack(side='left', padx=2)
        ttk.Label(date_lf, text="To:").pack(side='left', padx=2)
        self.sp_date_to_var = tk.StringVar()
        ttk.Entry(date_lf, textvariable=self.sp_date_to_var, width=12).pack(side='left', padx=2)

        today = datetime.now()
        first_of_month = f"{today.year}-{today.month:02d}-01"
        self.sp_date_from_var.set(first_of_month)
        self.sp_date_to_var.set(today.strftime("%Y-%m-%d"))

        for label, cmd in [
            ("This Month", self.sp_set_this_month),
            ("Last Month", self.sp_set_last_month),
            ("This Year",  self.sp_set_this_year),
            ("All Time",   self.sp_set_all_time),
        ]:
            ttk.Button(date_lf, text=label, command=cmd, width=10).pack(side='left', padx=2)

        ttk.Button(ctrl, text="🔄 Refresh", command=self.refresh_spending_plan).pack(side='left', padx=10)

        # Manual income override
        income_lf = ttk.LabelFrame(ctrl, text="Monthly Take-Home Pay", padding=5)
        income_lf.pack(side='left', padx=5)
        ttk.Label(income_lf, text="$").pack(side='left')
        self.sp_income_var = tk.StringVar(value="")
        ttk.Entry(income_lf, textvariable=self.sp_income_var, width=12).pack(side='left', padx=2)
        ttk.Label(income_lf, text="(leave blank to use detected income)").pack(side='left', padx=5)

        # ── 4 Bucket panels ───────────────────────────────────────────────────
        buckets_frame = ttk.Frame(plan_frame)
        buckets_frame.pack(fill='x', padx=5, pady=5)

        BUCKETS = [
            ("fixed",      "🏠 Fixed Costs",      "50–60%", (0.50, 0.60), "#4A90D9"),
            ("investment", "📈 Investments",       "10%",    (0.10, 0.10), "#27AE60"),
            ("savings",    "🏦 Savings",           "5–10%",  (0.05, 0.10), "#8E44AD"),
            ("guilt_free", "🎉 Guilt-Free Spend",  "20–35%", (0.20, 0.35), "#E67E22"),
        ]

        self.sp_bucket_labels = {}   # bucket_key → dict of label vars
        self.sp_bar_canvases = {}    # bucket_key → Canvas

        for col, (key, title, target_pct, target_range, color) in enumerate(BUCKETS):
            lf = ttk.LabelFrame(buckets_frame, text=title, padding=8)
            lf.grid(row=0, column=col, padx=6, pady=4, sticky='nsew')
            buckets_frame.columnconfigure(col, weight=1)

            ttk.Label(lf, text=f"Target: {target_pct} of income",
                      font=('Arial', 9, 'italic'), foreground='gray').pack()

            amt_var = tk.StringVar(value="$0.00")
            pct_var = tk.StringVar(value="0.0%")
            status_var = tk.StringVar(value="—")

            ttk.Label(lf, textvariable=amt_var, font=('Arial', 18, 'bold')).pack(pady=2)
            ttk.Label(lf, textvariable=pct_var, font=('Arial', 11)).pack()
            ttk.Label(lf, textvariable=status_var, font=('Arial', 10)).pack()

            # Progress bar canvas
            bar = tk.Canvas(lf, height=12, bg='#DDDDDD', highlightthickness=0)
            bar.pack(fill='x', pady=4)

            self.sp_bucket_labels[key] = {
                'amt': amt_var, 'pct': pct_var, 'status': status_var,
                'color': color, 'target_range': target_range
            }
            self.sp_bar_canvases[key] = bar

        # ── Category assignment ───────────────────────────────────────────────
        assign_lf = ttk.LabelFrame(plan_frame, text="Category → Bucket Assignment (right-click to reassign)", padding=5)
        assign_lf.pack(fill='both', expand=True, padx=5, pady=5)

        cols = ('Category', 'Bucket', 'Monthly Avg')
        self.sp_cat_tree = ttk.Treeview(assign_lf, columns=cols, show='headings', height=10)
        for c in cols:
            self.sp_cat_tree.heading(c, text=c)
        self.sp_cat_tree.column('Category', width=200)
        self.sp_cat_tree.column('Bucket', width=140)
        self.sp_cat_tree.column('Monthly Avg', width=110, anchor='e')

        sb = ttk.Scrollbar(assign_lf, orient='vertical', command=self.sp_cat_tree.yview)
        self.sp_cat_tree.configure(yscrollcommand=sb.set)
        self.sp_cat_tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self.sp_cat_tree.bind('<Button-2>', self.sp_show_bucket_menu)
        self.sp_cat_tree.bind('<Button-3>', self.sp_show_bucket_menu)

        self.refresh_spending_plan()

    def sp_set_this_month(self):
        from datetime import datetime
        today = datetime.now()
        self.sp_date_from_var.set(f"{today.year}-{today.month:02d}-01")
        self.sp_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_spending_plan()

    def sp_set_last_month(self):
        from datetime import datetime, timedelta
        today = datetime.now()
        first_this = datetime(today.year, today.month, 1)
        last_prev = first_this - timedelta(days=1)
        first_prev = datetime(last_prev.year, last_prev.month, 1)
        self.sp_date_from_var.set(first_prev.strftime("%Y-%m-%d"))
        self.sp_date_to_var.set(last_prev.strftime("%Y-%m-%d"))
        self.refresh_spending_plan()

    def sp_set_this_year(self):
        from datetime import datetime
        today = datetime.now()
        self.sp_date_from_var.set(f"{today.year}-01-01")
        self.sp_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_spending_plan()

    def sp_set_all_time(self):
        self.sp_date_from_var.set("")
        self.sp_date_to_var.set("")
        self.refresh_spending_plan()

    def refresh_spending_plan(self):
        """Recompute bucket totals and redraw the Spending Plan tab."""
        date_from = self.sp_date_from_var.get()
        date_to   = self.sp_date_to_var.get()

        conn   = self.db.get_connection()
        cursor = conn.cursor()

        # ── Determine income ──────────────────────────────────────────────────
        try:
            income = float(self.sp_income_var.get().replace(',', '').replace('$', ''))
        except (ValueError, AttributeError):
            income = 0.0

        if income <= 0:
            q = """SELECT SUM(amount) as total FROM transactions
                   WHERE transaction_type = 'income'"""
            p = []
            if date_from:
                q += " AND date >= ?"
                p.append(date_from)
            if date_to:
                q += " AND date <= ?"
                p.append(date_to)
            cursor.execute(q, p)
            row = cursor.fetchone()
            income = float(row['total'] or 0)

        # ── Spending per category ─────────────────────────────────────────────
        q = """SELECT t.category,
                      COALESCE(cb.bucket, 'guilt_free') as bucket,
                      SUM(ABS(t.amount)) as total
               FROM transactions t
               LEFT JOIN category_bucket cb ON t.category = cb.category
               WHERE t.transaction_type = 'expense'"""
        p = []
        if date_from:
            q += " AND t.date >= ?"
            p.append(date_from)
        if date_to:
            q += " AND t.date <= ?"
            p.append(date_to)
        q += " GROUP BY t.category ORDER BY total DESC"
        cursor.execute(q, p)
        cat_rows = cursor.fetchall()

        bucket_totals = {'fixed': 0.0, 'investment': 0.0, 'savings': 0.0,
                         'guilt_free': 0.0, 'untracked': 0.0}
        cat_buckets = {}
        for r in cat_rows:
            b = r['bucket'] or 'guilt_free'
            bucket_totals[b] = bucket_totals.get(b, 0) + float(r['total'] or 0)
            cat_buckets[r['category']] = (b, float(r['total'] or 0))

        # ── Update bucket panels ──────────────────────────────────────────────
        BUCKET_NAMES = {
            'fixed': 'Fixed Costs', 'investment': 'Investments',
            'savings': 'Savings', 'guilt_free': 'Guilt-Free'
        }
        for key, info in self.sp_bucket_labels.items():
            amt   = bucket_totals.get(key, 0)
            pct   = (amt / income * 100) if income > 0 else 0
            lo, hi = info['target_range']

            info['amt'].set(f"${amt:,.2f}")
            info['pct'].set(f"{pct:.1f}% of income")

            if income <= 0:
                status = "—"
            elif pct / 100 < lo:
                status = f"✅ Under target (target {lo*100:.0f}–{hi*100:.0f}%)"
            elif pct / 100 <= hi:
                status = f"✅ On target ({lo*100:.0f}–{hi*100:.0f}%)"
            else:
                status = f"⚠️ Over target (target {lo*100:.0f}–{hi*100:.0f}%)"
            info['status'].set(status)

            # Draw progress bar
            bar = self.sp_bar_canvases[key]
            bar.update_idletasks()
            w = bar.winfo_width() or 200
            fill_ratio = min(pct / 100 / hi, 1.5) if hi > 0 else 0  # cap at 150%
            fill_w = int(w * fill_ratio / 1.5)
            bar_color = info['color'] if pct / 100 <= hi else '#E74C3C'
            bar.delete('all')
            bar.create_rectangle(0, 0, fill_w, 12, fill=bar_color, outline='')
            # Target marker
            target_x = int(w / 1.5 * 1.0)  # 100% of target
            bar.create_line(target_x, 0, target_x, 12, fill='#333', width=2)

        # ── Populate category assignment tree ─────────────────────────────────
        BUCKET_DISPLAY = {
            'fixed': 'Fixed Costs', 'investment': 'Investments',
            'savings': 'Savings', 'guilt_free': 'Guilt-Free Spend',
            'untracked': 'Untracked'
        }
        for item in self.sp_cat_tree.get_children():
            self.sp_cat_tree.delete(item)

        for cat, (bucket, total) in sorted(cat_buckets.items(),
                                           key=lambda x: x[1][1], reverse=True):
            self.sp_cat_tree.insert('', 'end',
                iid=cat,
                values=(cat, BUCKET_DISPLAY.get(bucket, bucket), f"${total:,.2f}"))

        # Also show categories with bucket assignments but no spending this period
        cursor.execute("SELECT category, bucket FROM category_bucket ORDER BY category")
        for r in cursor.fetchall():
            if r['category'] not in cat_buckets:
                self.sp_cat_tree.insert('', 'end', iid=f"__{r['category']}",
                    values=(r['category'], BUCKET_DISPLAY.get(r['bucket'], r['bucket']), "$0.00"))

    def sp_show_bucket_menu(self, event):
        """Context menu to reassign a category to a different CSP bucket."""
        item = self.sp_cat_tree.identify_row(event.y)
        if not item:
            return
        self.sp_cat_tree.selection_set(item)
        cat_name = self.sp_cat_tree.item(item)['values'][0]

        BUCKET_OPTIONS = [
            ('Fixed Costs',       'fixed'),
            ('Investments',       'investment'),
            ('Savings',           'savings'),
            ('Guilt-Free Spend',  'guilt_free'),
            ('Untracked',         'untracked'),
        ]

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Assign '{cat_name}' to:", state='disabled')
        menu.add_separator()
        for label, key in BUCKET_OPTIONS:
            menu.add_command(
                label=label,
                command=lambda k=key, c=cat_name: self.sp_assign_bucket(c, k)
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def sp_assign_bucket(self, category, bucket):
        """Save a category → bucket assignment and refresh."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO category_bucket (category, bucket) VALUES (?, ?)",
            (category, bucket)
        )
        conn.commit()
        self.refresh_spending_plan()

    def set_cat_this_month(self):
        """Set category date range to current month"""
        from datetime import datetime
        today = datetime.now()
        self.cat_date_from_var.set(f"{today.year}-{today.month:02d}-01")
        self.cat_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_categories()

    def set_cat_last_month(self):
        """Set category date range to last month"""
        from datetime import datetime, timedelta

        today = datetime.now()

        # First day of current month
        first_this_month = datetime(today.year, today.month, 1)

        # Last day of last month
        last_day_last_month = first_this_month - timedelta(days=1)

        # First day of last month
        first_day_last_month = datetime(last_day_last_month.year, last_day_last_month.month, 1)

        self.cat_date_from_var.set(first_day_last_month.strftime("%Y-%m-%d"))
        self.cat_date_to_var.set(last_day_last_month.strftime("%Y-%m-%d"))
        self.refresh_categories()

    def set_cat_this_year(self):
        """Set category date range to current year"""
        from datetime import datetime
        today = datetime.now()
        self.cat_date_from_var.set(f"{today.year}-01-01")
        self.cat_date_to_var.set(today.strftime("%Y-%m-%d"))
        self.refresh_categories()

    def set_cat_all_time(self):
        """Clear category date range"""
        self.cat_date_from_var.set("")
        self.cat_date_to_var.set("")
        self.refresh_categories()

    def refresh_transactions(self):
        """Refresh transactions list"""
        # Clear tree
        for item in self.txn_tree.get_children():
            self.txn_tree.delete(item)

        # Get filter
        filter_text = self.filter_var.get()
        limit = self.limit_var.get()
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        account_filter = self.account_filter_var.get()

        # Refresh account dropdown with current DB accounts
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT account_name FROM transactions ORDER BY account_name")
        accounts = ["All Accounts"] + [r['account_name'] for r in cursor.fetchall()]
        self.account_combo['values'] = accounts
        if account_filter not in accounts:
            self.account_filter_var.set("All Accounts")
            account_filter = "All Accounts"

        # Build query
        query = "SELECT id, date, description, amount, category, account_name, transaction_type FROM transactions WHERE 1=1"
        params = []

        # Date range filter
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        # Account filter
        if account_filter and account_filter != "All Accounts":
            query += " AND account_name = ?"
            params.append(account_filter)

        # Text filter
        if filter_text:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([f"%{filter_text}%", f"%{filter_text}%"])

        query += " ORDER BY date DESC"

        if limit != "All":
            query += f" LIMIT {limit}"

        # Execute
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)

        # Populate
        for row in cursor.fetchall():
            self.txn_tree.insert(
                '',
                'end',
                text=str(row['id']),
                values=(
                    row['date'],
                    row['description'][:50],
                    f"${row['amount']:,.2f}",
                    row['category'],
                    row['account_name'],
                    row['transaction_type'] or ''
                )
            )

        count = len(self.txn_tree.get_children())

        # Calculate summary statistics
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Build same query for stats - exclude transfers from expense/income totals
        stats_query = """SELECT
            SUM(CASE WHEN amount < 0 AND (transaction_type = 'expense' OR transaction_type IS NULL) THEN ABS(amount) ELSE 0 END) as expenses,
            SUM(CASE WHEN amount > 0 AND (transaction_type = 'income' OR transaction_type IS NULL) THEN amount ELSE 0 END) as income,
            COUNT(*) as count FROM transactions WHERE 1=1"""
        stats_params = []

        if date_from:
            stats_query += " AND date >= ?"
            stats_params.append(date_from)

        if date_to:
            stats_query += " AND date <= ?"
            stats_params.append(date_to)

        if account_filter and account_filter != "All Accounts":
            stats_query += " AND account_name = ?"
            stats_params.append(account_filter)

        if filter_text:
            stats_query += " AND (description LIKE ? OR category LIKE ?)"
            stats_params.extend([f"%{filter_text}%", f"%{filter_text}%"])

        cursor.execute(stats_query, stats_params)
        stats = cursor.fetchone()

        expenses = stats['expenses'] or 0
        income = stats['income'] or 0
        net = income - expenses

        # Update status with summary
        status = f"Showing {count} transactions"
        if date_from or date_to:
            if date_from and date_to:
                status += f" ({date_from} to {date_to})"
            elif date_from:
                status += f" (from {date_from})"
            elif date_to:
                status += f" (to {date_to})"

        status += f" | Expenses: ${expenses:,.2f} | Income: ${income:,.2f} | Net: ${net:,.2f}"

        self.status_var.set(status)

    def add_transaction(self):
        """Add a new transaction manually"""
        AddTransactionDialog(self.root, self.db, self.refresh_transactions)

    def edit_transaction(self, event):
        """Edit selected transaction"""
        selection = self.txn_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transaction to edit")
            return

        item = selection[0]
        txn_id = self.txn_tree.item(item)['text']

        # Get transaction details
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,))
        txn = cursor.fetchone()

        if not txn:
            return

        # Create edit dialog
        EditTransactionDialog(self.root, self.db, txn, self.refresh_transactions, self.learned_rules, self.refresh_rules)

    def delete_transaction(self):
        """Delete selected transaction"""
        selection = self.txn_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transaction to delete")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction?"):
            return

        item = selection[0]
        txn_id = self.txn_tree.item(item)['text']

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        conn.commit()

        self.refresh_transactions()
        self.status_var.set("Transaction deleted")

    # Rules functions

    def refresh_rules(self):
        """Refresh rules list"""
        # Clear tree
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        # Get learned rules
        rules = self.learned_rules.get_all_rules()

        # Count transactions per rule
        conn = self.db.get_connection()
        cursor = conn.cursor()

        for category, keywords in sorted(rules.items()):
            # Count transactions
            cursor.execute(
                "SELECT COUNT(*) as count FROM transactions WHERE category = ?",
                (category,)
            )
            count = cursor.fetchone()['count']

            self.rules_tree.insert(
                '',
                'end',
                text=category,
                values=(', '.join(keywords[:5]), count)
            )

        self.status_var.set(f"Loaded {len(rules)} rules")

    def add_rule(self):
        """Add a new rule"""
        self.rule_category_var.set("")
        self.rule_keyword_var.set("")

    def edit_rule(self):
        """Edit selected rule"""
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to edit")
            return

        item = selection[0]
        category = self.rules_tree.item(item)['text']

        # Get keywords for this category
        rules = self.learned_rules.get_all_rules()

        if category not in rules:
            messagebox.showwarning("Not Found", f"No rules found for '{category}'")
            return

        # Create callback that reloads rules in main app
        def on_save():
            # Reload learned rules in main app
            self.learned_rules = LearnedRules()
            self.refresh_rules()

        # Open edit dialog
        EditRuleDialog(self.root, self.learned_rules, category, rules[category], on_save)

    def save_rule(self):
        """Save the current rule"""
        category = self.rule_category_var.get().strip()
        keyword = self.rule_keyword_var.get().strip().upper()

        if not category or not keyword:
            messagebox.showwarning("Missing Information", "Please enter both category and keyword")
            return

        self.learned_rules.add_rule(category, keyword)  # CORRECT ORDER: category, keyword

        self.rule_category_var.set("")
        self.rule_keyword_var.set("")

        self.refresh_rules()
        self.status_var.set(f"Added rule: {keyword} → {category}")

        messagebox.showinfo("Rule Added", f"Added rule: {keyword} → {category}")

    def delete_rule(self):
        """Delete selected rule"""
        selection = self.rules_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a rule to delete")
            return

        item = selection[0]
        category = self.rules_tree.item(item)['text']

        if messagebox.askyesno("Confirm Delete", f"Delete all rules for '{category}'?"):
            # Load the rules file directly
            import json
            from pathlib import Path

            rules_file = Path("data/learned_rules.json")

            if rules_file.exists():
                with open(rules_file, 'r') as f:
                    rules = json.load(f)

                # Delete the category
                if category in rules:
                    keyword_count = len(rules[category])
                    del rules[category]

                    # Save back to file
                    with open(rules_file, 'w') as f:
                        json.dump(rules, f, indent=2)

                    # Reload in memory
                    self.learned_rules = LearnedRules()

                    self.refresh_rules()
                    self.status_var.set(f"Deleted {keyword_count} rule(s) for: {category}")
                    messagebox.showinfo("Deleted", f"Deleted {keyword_count} keyword(s) for '{category}'")
                else:
                    messagebox.showwarning("Not Found", f"No rules found for '{category}'")
            else:
                messagebox.showwarning("Not Found", "No rules file found")

    def show_category_transactions(self, event):
        """Show all transactions for the selected category"""
        selection = self.cat_tree.selection()
        if not selection:
            return

        # Get selected category
        item = selection[0]
        category = self.cat_tree.item(item)['text']

        # Switch to Transactions tab
        self.notebook.select(2)  # Index 2 = Transactions tab (0=Import, 1=Dashboard, 2=Transactions)

        # Clear date range to show ALL transactions
        self.date_from_var.set("")
        self.date_to_var.set("")

        # Set filter to category
        self.filter_var.set(category)

        # Set limit to show more results
        self.limit_var.set("All")

        # Refresh transactions to show filtered results
        self.refresh_transactions()

        # Update status
        self.status_var.set(f"Showing ALL transactions for category: {category}")

    def show_category_menu(self, event):
        """Show context menu for category"""
        # Select the item under cursor
        item = self.cat_tree.identify_row(event.y)
        if item:
            self.cat_tree.selection_set(item)
            category = self.cat_tree.item(item)['text']

            # Get current date range
            date_from = self.cat_date_from_var.get()
            date_to = self.cat_date_to_var.get()

            # Create context menu
            menu = tk.Menu(self.root, tearoff=0)

            # Option 1: All transactions
            menu.add_command(
                label=f"View ALL '{category}' transactions",
                command=lambda: self.show_category_transactions(None)
            )

            # Option 2: Current period only (if date range is set)
            if date_from or date_to:
                period_label = ""
                if date_from and date_to:
                    period_label = f" ({date_from} to {date_to})"
                elif date_from:
                    period_label = f" (from {date_from})"
                elif date_to:
                    period_label = f" (to {date_to})"

                menu.add_command(
                    label=f"View '{category}' for current period{period_label}",
                    command=lambda: self.show_category_transactions_period(category, date_from, date_to)
                )

            menu.add_separator()
            menu.add_command(
                label="Export category to CSV",
                command=lambda: self.export_category(category)
            )

            # Show menu at cursor position
            menu.post(event.x_root, event.y_root)

    def show_category_transactions_period(self, category, date_from, date_to):
        """Show transactions for category within specific date range"""
        # Switch to Transactions tab
        self.notebook.select(2)

        # Set date range
        self.date_from_var.set(date_from or "")
        self.date_to_var.set(date_to or "")

        # Set filter to category
        self.filter_var.set(category)

        # Set limit
        self.limit_var.set("All")

        # Refresh
        self.refresh_transactions()

        # Update status
        period = ""
        if date_from and date_to:
            period = f" ({date_from} to {date_to})"
        elif date_from:
            period = f" (from {date_from})"
        elif date_to:
            period = f" (to {date_to})"

        self.status_var.set(f"Showing '{category}' transactions{period}")

    def export_category(self, category):
        """Export all transactions in a category to CSV"""
        from tkinter import filedialog
        import csv
        from datetime import datetime

        # Get date range
        date_from = self.cat_date_from_var.get()
        date_to = self.cat_date_to_var.get()

        # Build query
        query = "SELECT * FROM transactions WHERE category = ?"
        params = [category]

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY date DESC"

        # Get transactions
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        transactions = cursor.fetchall()

        if not transactions:
            messagebox.showinfo("No Data", f"No transactions found in category '{category}'")
            return

        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{category.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if not filename:
            return

        # Write to CSV
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Date', 'Description', 'Amount', 'Category', 'Account', 'Type', 'Notes'])

                # Data
                for txn in transactions:
                    writer.writerow([
                        txn['date'],
                        txn['description'],
                        txn['amount'],
                        txn['category'],
                        txn['account_name'],
                        txn['transaction_type'] or '',
                        txn['notes'] or ''
                    ])

            messagebox.showinfo(
                "Export Complete",
                f"Exported {len(transactions)} transactions to:\n{filename}"
            )

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n\n{str(e)}")

    # Categories functions

    def refresh_categories(self):
        """Refresh categories list"""
        # Clear tree
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)

        # Get date range
        date_from = self.cat_date_from_var.get()
        date_to = self.cat_date_to_var.get()

        # Get stats
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Build query with date filters - get both expenses and income per category
        query = """
            SELECT 
                category,
                COUNT(*) as count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
            FROM transactions
            WHERE category NOT IN ('Credit Card Payment', 'Transfer')
              AND (transaction_type != 'transfer' OR transaction_type IS NULL)
        """
        params = []

        if date_from:
            query += " AND date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += """
            GROUP BY category
            HAVING expenses > 0 OR income > 0
            ORDER BY (expenses - income) DESC
        """

        cursor.execute(query, params)

        results = cursor.fetchall()
        total_net_spending = sum(row['expenses'] - row['income'] for row in results)

        # Store data for chart
        chart_data = []

        for row in results:
            expenses = row['expenses'] or 0
            income = row['income'] or 0
            net = expenses - income

            # Calculate percentage based on net spending
            percentage = (net / total_net_spending * 100) if total_net_spending > 0 else 0

            self.cat_tree.insert(
                '',
                'end',
                text=row['category'],
                values=(
                    row['count'],
                    f"${expenses:,.2f}",
                    f"${income:,.2f}" if income > 0 else "-",
                    f"${net:,.2f}",
                    f"{percentage:.1f}%"
                )
            )

            # Only include in chart if net spending is positive
            if net > 0:
                chart_data.append({
                    'category': row['category'],
                    'total': net,
                    'percent': percentage
                })

        # Draw chart
        self.draw_category_chart(chart_data)

        # Update status with total and date range
        total_expenses = sum(row['expenses'] for row in results)
        total_income = sum(row['income'] for row in results)

        status = f"Total expenses: ${total_expenses:,.2f} | Total income: ${total_income:,.2f} | Net spending: ${total_net_spending:,.2f}"
        if date_from or date_to:
            if date_from and date_to:
                status += f" ({date_from} to {date_to})"
            elif date_from:
                status += f" (from {date_from})"
            elif date_to:
                status += f" (to {date_to})"

        self.status_var.set(status)

    def draw_category_chart(self, data):
        """Draw horizontal bar chart of category spending"""
        # Clear canvas
        self.cat_chart_canvas.delete('all')

        if not data:
            return

        # Get canvas dimensions
        canvas_width = self.cat_chart_canvas.winfo_width()
        canvas_height = 200

        # Use actual width if available, otherwise use default
        if canvas_width < 100:
            canvas_width = 800

        # Show top 10 categories
        top_data = data[:10]

        # Calculate bar dimensions
        bar_height = 15
        bar_spacing = 5
        left_margin = 150
        right_margin = 100
        top_margin = 10

        max_amount = max(d['total'] for d in top_data) if top_data else 1
        chart_width = canvas_width - left_margin - right_margin

        # Colors
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#ABEBC6'
        ]

        y = top_margin

        for i, item in enumerate(top_data):
            # Calculate bar width
            bar_width = (item['total'] / max_amount * chart_width) if max_amount > 0 else 0

            # Color
            color = colors[i % len(colors)]

            # Category label (left)
            self.cat_chart_canvas.create_text(
                left_margin - 10,
                y + bar_height / 2,
                text=item['category'][:20],
                anchor='e',
                font=('Arial', 9),
                fill='black'
            )

            # Bar
            self.cat_chart_canvas.create_rectangle(
                left_margin,
                y,
                left_margin + bar_width,
                y + bar_height,
                fill=color,
                outline=''
            )

            # Amount and percentage (right)
            label = f"${item['total']:,.0f} ({item['percent']:.1f}%)"
            self.cat_chart_canvas.create_text(
                left_margin + bar_width + 5,
                y + bar_height / 2,
                text=label,
                anchor='w',
                font=('Arial', 9, 'bold'),
                fill='black'
            )

            y += bar_height + bar_spacing


class AddTransactionDialog:
    """Dialog for adding a new transaction manually"""

    def __init__(self, parent, db, callback):
        self.db = db
        self.callback = callback

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Transaction")
        self.dialog.geometry("500x500")

        # Title
        ttk.Label(
            self.dialog,
            text="Add New Transaction",
            font=('Arial', 14, 'bold')
        ).pack(pady=20)

        # Form
        form = ttk.Frame(self.dialog)
        form.pack(fill='both', expand=True, padx=20, pady=10)

        row = 0

        # Date (required)
        ttk.Label(form, text="Date: *", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)
        self.date_var = tk.StringVar()

        # Default to today
        from datetime import datetime
        self.date_var.set(datetime.now().strftime("%Y-%m-%d"))

        date_entry = ttk.Entry(form, textvariable=self.date_var, width=30)
        date_entry.grid(row=row, column=1, sticky='w', pady=5)
        ttk.Label(form, text="(YYYY-MM-DD)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', padx=5)
        row += 1

        # Description (required)
        ttk.Label(form, text="Description: *", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)
        self.description_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Amount (required)
        ttk.Label(form, text="Amount: *", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)
        self.amount_var = tk.StringVar()
        amount_frame = ttk.Frame(form)
        amount_frame.grid(row=row, column=1, sticky='w', pady=5)

        ttk.Entry(amount_frame, textvariable=self.amount_var, width=15).pack(side='left')
        ttk.Label(amount_frame, text="(negative for expenses)", font=('Arial', 8)).pack(side='left', padx=5)
        row += 1

        # Category
        ttk.Label(form, text="Category:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)

        # Get existing categories
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category")
        existing_categories = [r['category'] for r in cursor.fetchall()]

        self.category_var = tk.StringVar(value="Uncategorized")
        self.category_combo = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=existing_categories,
            width=28
        )
        self.category_combo.grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Account
        ttk.Label(form, text="Account:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)

        # Get existing accounts
        cursor.execute(
            "SELECT DISTINCT account_name FROM transactions WHERE account_name IS NOT NULL ORDER BY account_name")
        existing_accounts = [r['account_name'] for r in cursor.fetchall()]

        # Add "Cash" as default option
        if "Cash" not in existing_accounts:
            existing_accounts.insert(0, "Cash")

        self.account_var = tk.StringVar(value="Cash")
        self.account_combo = ttk.Combobox(
            form,
            textvariable=self.account_var,
            values=existing_accounts,
            width=28
        )
        self.account_combo.grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Transaction Type
        ttk.Label(form, text="Type:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)
        self.type_var = tk.StringVar(value="expense")
        type_frame = ttk.Frame(form)
        type_frame.grid(row=row, column=1, sticky='w', pady=5)

        ttk.Radiobutton(type_frame, text="Expense", variable=self.type_var, value="expense").pack(side='left', padx=5)
        ttk.Radiobutton(type_frame, text="Income", variable=self.type_var, value="income").pack(side='left', padx=5)
        ttk.Radiobutton(type_frame, text="Transfer", variable=self.type_var, value="transfer").pack(side='left', padx=5)
        row += 1

        # Tags
        ttk.Label(form, text="Tags:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=5)
        self.tags_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.tags_var, width=30).grid(row=row, column=1, sticky='w', pady=5)
        ttk.Label(form, text="(comma-separated)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', padx=5)
        row += 1

        # Notes
        ttk.Label(form, text="Notes:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky='nw', pady=5)
        self.notes_text = tk.Text(form, height=4, width=30)
        self.notes_text.grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Required fields note
        ttk.Label(
            form,
            text="* Required fields",
            font=('Arial', 8, 'italic'),
            foreground='gray'
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=10)

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="💾 Save", command=self.save, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="❌ Cancel", command=self.dialog.destroy, width=15).pack(side='left', padx=5)

    def save(self):
        """Save the new transaction"""
        # Validate required fields
        date = self.date_var.get().strip()
        description = self.description_var.get().strip()
        amount_str = self.amount_var.get().strip()

        if not date:
            messagebox.showwarning("Missing Date", "Please enter a date")
            return

        if not description:
            messagebox.showwarning("Missing Description", "Please enter a description")
            return

        if not amount_str:
            messagebox.showwarning("Missing Amount", "Please enter an amount")
            return

        # Validate amount
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid number for amount")
            return

        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date", "Please enter date in YYYY-MM-DD format")
            return

        # Get other fields
        category = self.category_var.get().strip() or "Uncategorized"
        account = self.account_var.get().strip() or "Cash"
        txn_type = self.type_var.get()
        tags = self.tags_var.get().strip()
        notes = self.notes_text.get('1.0', 'end').strip()

        # Insert into database
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transactions
            (date, description, amount, account_name, account_type, institution, category, transaction_type, tags, notes, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date, description, amount, account,
            'Manual', 'Manual Entry',
            category, txn_type, tags or None, notes or None, None
        ))

        conn.commit()

        # Close dialog
        self.dialog.destroy()

        # Refresh transactions list
        self.callback()

        # Show confirmation
        messagebox.showinfo("Transaction Added", f"Added transaction: {description} - ${amount:,.2f}")


class EditTransactionDialog:
    """Dialog for editing a transaction"""

    def __init__(self, parent, db, txn, callback, learned_rules=None, rules_callback=None):
        self.db = db
        self.txn = txn
        self.callback = callback
        self.learned_rules = learned_rules
        self.rules_callback = rules_callback

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Transaction")
        self.dialog.geometry("500x400")

        # Form
        form = ttk.Frame(self.dialog)
        form.pack(fill='both', expand=True, padx=20, pady=20)

        row = 0

        # Date
        ttk.Label(form, text="Date:").grid(row=row, column=0, sticky='w', pady=5)
        ttk.Label(form, text=txn['date']).grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Description
        ttk.Label(form, text="Description:").grid(row=row, column=0, sticky='w', pady=5)
        ttk.Label(form, text=txn['description'][:50]).grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Amount
        ttk.Label(form, text="Amount:").grid(row=row, column=0, sticky='w', pady=5)
        ttk.Label(form, text=f"${txn['amount']:,.2f}").grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        # Category (editable with autocomplete)
        ttk.Label(form, text="Category:").grid(row=row, column=0, sticky='w', pady=5)

        # Get existing categories for autocomplete
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category")
        existing_categories = [row['category'] for row in cursor.fetchall()]

        self.category_var = tk.StringVar(value=txn['category'])
        self.category_combo = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=existing_categories,
            width=28
        )
        self.category_combo.grid(row=row, column=1, sticky='w', pady=5)

        # Enable autocomplete - filter as you type
        def on_category_change(event):
            typed = self.category_var.get().lower()
            if typed == '':
                self.category_combo['values'] = existing_categories
            else:
                # Filter categories that start with or contain the typed text
                filtered = [cat for cat in existing_categories
                            if typed in cat.lower()]
                self.category_combo['values'] = filtered

        self.category_combo.bind('<KeyRelease>', on_category_change)
        row += 1

        # Transaction Type (editable)
        ttk.Label(form, text="Type:").grid(row=row, column=0, sticky='w', pady=5)

        type_frame = ttk.Frame(form)
        type_frame.grid(row=row, column=1, sticky='w', pady=5)

        self.type_var = tk.StringVar(value=txn['transaction_type'] or 'expense')

        ttk.Radiobutton(
            type_frame,
            text="Expense",
            variable=self.type_var,
            value="expense"
        ).pack(side='left', padx=5)

        ttk.Radiobutton(
            type_frame,
            text="Income",
            variable=self.type_var,
            value="income"
        ).pack(side='left', padx=5)

        ttk.Radiobutton(
            type_frame,
            text="Transfer",
            variable=self.type_var,
            value="transfer"
        ).pack(side='left', padx=5)

        row += 1

        # Tags (editable)
        ttk.Label(form, text="Tags:").grid(row=row, column=0, sticky='w', pady=5)
        self.tags_var = tk.StringVar(value=txn['tags'] if txn['tags'] else '')
        ttk.Entry(form, textvariable=self.tags_var, width=30).grid(row=row, column=1, sticky='w', pady=5)
        ttk.Label(form, text="(comma-separated)", font=('Arial', 8)).grid(row=row, column=2, sticky='w', padx=5)
        row += 1

        # Notes (editable)
        ttk.Label(form, text="Notes:").grid(row=row, column=0, sticky='nw', pady=5)
        self.notes_text = tk.Text(form, height=4, width=30)
        self.notes_text.grid(row=row, column=1, sticky='w', pady=5)
        if txn['notes']:
            self.notes_text.insert('1.0', txn['notes'])
        row += 1

        # Buttons
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="💾 Save", command=self.save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="❌ Cancel", command=self.dialog.destroy).pack(side='left', padx=5)

    def save(self):
        """Save changes"""
        new_category = self.category_var.get()
        new_type = self.type_var.get()
        new_tags = self.tags_var.get().strip() or None
        new_notes = self.notes_text.get('1.0', 'end').strip() or None
        old_category = self.txn['category']
        old_type = self.txn['transaction_type']

        # Check if category changed
        category_changed = (new_category != old_category)
        type_changed = (new_type != old_type)

        # Update this transaction
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE transactions SET category = ?, transaction_type = ?, tags = ?, notes = ? WHERE id = ?",
            (new_category, new_type, new_tags, new_notes, self.txn['id'])
        )

        conn.commit()

        # If category changed, offer to learn rule and apply to all
        if category_changed and new_category != 'Uncategorized' and self.learned_rules:
            learned_rules = self.learned_rules

            # Suggest a keyword
            suggested_keyword = learned_rules.suggest_rule(self.txn['description'], new_category)

            if suggested_keyword:
                # Ask user if they want to learn this rule and apply to all
                msg = f"Learn this categorization rule?\n\n"
                msg += f"Keyword: '{suggested_keyword}'\n"
                msg += f"Category: '{new_category}'\n\n"

                # Count how many other transactions match
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM transactions
                    WHERE description LIKE ? AND category != ? AND id != ?
                """, (f'%{suggested_keyword}%', new_category, self.txn['id']))

                match_count = cursor.fetchone()['count']

                if match_count > 0:
                    msg += f"This will also update {match_count} other transaction(s)\n"
                    msg += f"with '{suggested_keyword}' in the description.\n\n"
                    msg += f"Learn rule and apply to all matching transactions?"
                else:
                    msg += f"Learn rule for future transactions?"

                from tkinter import messagebox
                if messagebox.askyesno("Learn Rule?", msg):
                    # Save the rule (CORRECT ORDER: category, keyword)
                    learned_rules.add_rule(new_category, suggested_keyword)

                    # Apply to all matching transactions
                    if match_count > 0:
                        cursor.execute("""
                            UPDATE transactions
                            SET category = ?
                            WHERE description LIKE ? AND category != ?
                        """, (new_category, f'%{suggested_keyword}%', new_category))

                        conn.commit()

                        messagebox.showinfo(
                            "Rule Applied",
                            f"✅ Learned rule: '{suggested_keyword}' → '{new_category}'\n\n" +
                            f"Updated {match_count + 1} transaction(s) total"
                        )
                    else:
                        messagebox.showinfo(
                            "Rule Saved",
                            f"✅ Learned rule: '{suggested_keyword}' → '{new_category}'\n\n" +
                            f"This will apply to future imports"
                        )

        self.dialog.destroy()
        self.callback()
        if self.rules_callback:
            self.rules_callback()


class EditRuleDialog:
    """Dialog for editing a categorization rule"""

    def __init__(self, parent, learned_rules, category, keywords, callback):
        self.learned_rules = learned_rules
        self.category = category
        self.keywords = keywords.copy()
        self.callback = callback

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Rule: {category}")
        self.dialog.geometry("500x400")

        # Category name (editable)
        ttk.Label(
            self.dialog,
            text="Category:",
            font=('Arial', 10, 'bold')
        ).pack(pady=(20, 5))

        self.category_var = tk.StringVar(value=category)
        ttk.Entry(
            self.dialog,
            textvariable=self.category_var,
            width=40,
            font=('Arial', 12)
        ).pack(pady=5)

        # Keywords list
        ttk.Label(
            self.dialog,
            text="Keywords:",
            font=('Arial', 10, 'bold')
        ).pack(pady=(20, 5))

        # Frame for listbox and scrollbar
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill='both', expand=True, padx=20, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')

        self.keywords_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Arial', 11)
        )
        self.keywords_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.keywords_listbox.yview)

        # Populate keywords
        for kw in self.keywords:
            self.keywords_listbox.insert('end', kw)

        # Keyword management buttons
        kw_btn_frame = ttk.Frame(self.dialog)
        kw_btn_frame.pack(pady=10)

        ttk.Button(
            kw_btn_frame,
            text="➕ Add Keyword",
            command=self.add_keyword
        ).pack(side='left', padx=5)

        ttk.Button(
            kw_btn_frame,
            text="🗑️ Remove Selected",
            command=self.remove_keyword
        ).pack(side='left', padx=5)

        # Save/Cancel buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="💾 Save Changes",
            command=self.save
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="❌ Cancel",
            command=self.dialog.destroy
        ).pack(side='left', padx=5)

    def add_keyword(self):
        """Add a new keyword to the list"""
        from tkinter import simpledialog

        keyword = simpledialog.askstring(
            "Add Keyword",
            "Enter keyword:",
            parent=self.dialog
        )

        if keyword:
            keyword = keyword.strip().upper()
            if keyword and keyword not in self.keywords:
                self.keywords.append(keyword)
                self.keywords_listbox.insert('end', keyword)
            elif keyword in self.keywords:
                messagebox.showwarning("Duplicate", f"Keyword '{keyword}' already exists")

    def remove_keyword(self):
        """Remove selected keyword from the list"""
        selection = self.keywords_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a keyword to remove")
            return

        idx = selection[0]
        keyword = self.keywords_listbox.get(idx)

        if messagebox.askyesno("Confirm", f"Remove keyword '{keyword}'?"):
            self.keywords.remove(keyword)
            self.keywords_listbox.delete(idx)

    def save(self):
        """Save changes to the rule"""
        new_category = self.category_var.get().strip()

        if not new_category:
            messagebox.showwarning("Missing Category", "Please enter a category name")
            return

        if not self.keywords:
            messagebox.showwarning("No Keywords", "Please add at least one keyword")
            return

        # Load rules file
        import json
        from pathlib import Path

        rules_file = Path("data/learned_rules.json")

        if rules_file.exists():
            with open(rules_file, 'r') as f:
                rules = json.load(f)
        else:
            rules = {}

        # If category name changed, delete old category
        if new_category != self.category and self.category in rules:
            del rules[self.category]

        # Update with new keywords
        rules[new_category] = self.keywords

        # Save
        with open(rules_file, 'w') as f:
            json.dump(rules, f, indent=2)

        # Close dialog first
        self.dialog.destroy()

        # Then refresh (this reloads LearnedRules in main app)
        self.callback()

        # Show confirmation
        messagebox.showinfo(
            "Saved",
            f"Updated rule for '{new_category}' with {len(self.keywords)} keyword(s)"
        )


class MergeCategoriesDialog:
    """Dialog for merging categories"""

    def __init__(self, parent, db, callback1, callback2):
        self.db = db
        self.callback1 = callback1
        self.callback2 = callback2

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Merge Categories")
        self.dialog.geometry("600x500")

        # Instructions
        ttk.Label(
            self.dialog,
            text="Merge Categories",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)

        ttk.Label(
            self.dialog,
            text="Select categories to merge into a single category",
            font=('Arial', 10)
        ).pack(pady=5)

        # Get all categories
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM transactions
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY category
        """)
        self.categories = cursor.fetchall()

        # Frame for lists
        lists_frame = ttk.Frame(self.dialog)
        lists_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Left: Source categories (to merge)
        left_frame = ttk.Frame(lists_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)

        ttk.Label(left_frame, text="Categories to Merge:", font=('Arial', 10, 'bold')).pack()

        self.source_listbox = tk.Listbox(left_frame, selectmode='multiple', height=15)
        self.source_listbox.pack(fill='both', expand=True, pady=5)

        for cat in self.categories:
            self.source_listbox.insert('end', f"{cat['category']} ({cat['count']})")

        # Right: Target category (merge into)
        right_frame = ttk.Frame(lists_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5)

        ttk.Label(right_frame, text="Merge Into:", font=('Arial', 10, 'bold')).pack()

        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(
            right_frame,
            textvariable=self.target_var,
            values=[cat['category'] for cat in self.categories],
            width=30
        )
        self.target_combo.pack(pady=5)

        ttk.Label(right_frame, text="Or enter new category name:").pack(pady=(20, 5))

        # Preview
        self.preview_text = scrolledtext.ScrolledText(right_frame, height=10, width=30)
        self.preview_text.pack(fill='both', expand=True, pady=5)

        # Update preview when selection changes
        self.source_listbox.bind('<<ListboxSelect>>', self.update_preview)

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="🔀 Merge", command=self.merge).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="❌ Cancel", command=self.dialog.destroy).pack(side='left', padx=5)

    def update_preview(self, event=None):
        """Update merge preview"""
        self.preview_text.delete('1.0', 'end')

        selected = self.source_listbox.curselection()
        if not selected:
            self.preview_text.insert('end', "Select categories to merge...")
            return

        target = self.target_var.get()
        if not target:
            self.preview_text.insert('end', "Enter target category name...")
            return

        self.preview_text.insert('end', f"Will merge:\n\n")

        total_txns = 0
        for idx in selected:
            cat = self.categories[idx]
            self.preview_text.insert('end', f"• {cat['category']} ({cat['count']} txns)\n")
            total_txns += cat['count']

        self.preview_text.insert('end', f"\n→ Into: {target}\n")
        self.preview_text.insert('end', f"\nTotal: {total_txns} transactions")

    def merge(self):
        """Perform the merge"""
        selected = self.source_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select categories to merge")
            return

        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("No Target", "Please enter target category name")
            return

        # Get selected category names
        source_cats = [self.categories[idx]['category'] for idx in selected]

        # Don't merge if target is in source
        if target in source_cats and len(source_cats) == 1:
            messagebox.showwarning("Invalid Merge", "Cannot merge category into itself")
            return

        # Confirm
        total = sum(self.categories[idx]['count'] for idx in selected)
        msg = f"Merge {len(source_cats)} categories into '{target}'?\n\n"
        msg += f"This will update {total} transactions."

        if not messagebox.askyesno("Confirm Merge", msg):
            return

        # Perform merge
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Save mappings for future imports
        from src.category_mapper import CategoryMapper
        mapper = CategoryMapper()

        for cat in source_cats:
            if cat != target:  # Don't update if already the target
                cursor.execute(
                    "UPDATE transactions SET category = ? WHERE category = ?",
                    (target, cat)
                )
                # Remember this mapping for future imports
                mapper.add_mapping(cat, target)

        conn.commit()

        self.dialog.destroy()
        self.callback1()
        self.callback2()

        messagebox.showinfo("Merge Complete", f"Merged {len(source_cats)} categories into '{target}'")


class DuplicateReviewDialog:
    """Dialog for reviewing and deleting duplicate transactions"""

    def __init__(self, parent, db, callback):
        self.db = db
        self.callback = callback

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Review Duplicates")
        self.dialog.geometry("900x600")

        # Title
        ttk.Label(
            self.dialog,
            text="Review Duplicate Transactions",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)

        # Instructions
        ttk.Label(
            self.dialog,
            text="Select duplicates to DELETE (keep one, delete the rest)",
            font=('Arial', 10)
        ).pack(pady=5)

        # Get duplicates
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, description, amount, GROUP_CONCAT(id) as ids, GROUP_CONCAT(account_name, ' | ') as accounts, COUNT(*) as count
            FROM transactions
            GROUP BY date, description, amount
            HAVING count > 1
            ORDER BY date DESC
        """)

        self.duplicate_groups = cursor.fetchall()

        # Tree view
        tree_frame = ttk.Frame(self.dialog)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.dup_tree = ttk.Treeview(
            tree_frame,
            columns=('date', 'description', 'amount', 'count', 'accounts'),
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode='extended'
        )

        vsb.config(command=self.dup_tree.yview)
        hsb.config(command=self.dup_tree.xview)

        self.dup_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Configure columns
        self.dup_tree.heading('#0', text='Select')
        self.dup_tree.heading('date', text='Date')
        self.dup_tree.heading('description', text='Description')
        self.dup_tree.heading('amount', text='Amount')
        self.dup_tree.heading('count', text='Copies')
        self.dup_tree.heading('accounts', text='Accounts')

        self.dup_tree.column('#0', width=50)
        self.dup_tree.column('date', width=100)
        self.dup_tree.column('description', width=300)
        self.dup_tree.column('amount', width=80)
        self.dup_tree.column('count', width=60)
        self.dup_tree.column('accounts', width=200)

        # Populate with duplicate groups
        for group in self.duplicate_groups:
            # Insert parent (the duplicate group)
            parent_id = self.dup_tree.insert(
                '',
                'end',
                text='',
                values=(
                    group['date'],
                    group['description'][:50],
                    f"${group['amount']}",
                    f"{group['count']} copies",
                    ''
                ),
                tags=('group',)
            )

            # Get all transactions in this group
            ids = group['ids'].split(',')
            for txn_id in ids:
                cursor.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,))
                txn = cursor.fetchone()

                # Insert child (individual transaction)
                self.dup_tree.insert(
                    parent_id,
                    'end',
                    text=txn['id'],
                    values=(
                        txn['date'],
                        txn['description'][:50],
                        f"${txn['amount']}",
                        '',
                        txn['account_name']
                    ),
                    tags=('transaction',)
                )

        # Style
        self.dup_tree.tag_configure('group', background='#E8E8E8')

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)

        ttk.Label(btn_frame, text="For each duplicate group, keep 1 and select the others to delete →").pack(
            side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="🗑️ Delete Selected",
            command=self.delete_selected
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="🔄 Auto-Delete Extras",
            command=self.auto_delete_extras
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="❌ Close",
            command=self.dialog.destroy
        ).pack(side='left', padx=5)

    def delete_selected(self):
        """Delete selected transactions"""
        selected = self.dup_tree.selection()

        if not selected:
            messagebox.showwarning("No Selection", "Please select transactions to delete")
            return

        # Get IDs to delete (only children, not groups)
        ids_to_delete = []
        for item in selected:
            item_id = self.dup_tree.item(item)['text']
            if item_id:  # Only if it has an ID (is a transaction, not a group)
                ids_to_delete.append(item_id)

        if not ids_to_delete:
            messagebox.showwarning("No Transactions", "Please select individual transactions (not groups)")
            return

        msg = f"Delete {len(ids_to_delete)} selected transaction(s)?\n\n"
        msg += "This cannot be undone!"

        if messagebox.askyesno("Confirm Delete", msg):
            conn = self.db.get_connection()
            cursor = conn.cursor()

            for txn_id in ids_to_delete:
                cursor.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))

            conn.commit()

            # Remove from tree
            for item in selected:
                self.dup_tree.delete(item)

            messagebox.showinfo("Deleted", f"Deleted {len(ids_to_delete)} transaction(s)")

            # Refresh parent window
            self.callback()

    def auto_delete_extras(self):
        """Automatically keep first transaction in each group, delete the rest"""
        msg = "Auto-delete duplicates?\n\n"
        msg += "This will:\n"
        msg += "• Keep the FIRST transaction in each duplicate group\n"
        msg += "• Delete all other copies\n\n"
        msg += f"Found {len(self.duplicate_groups)} duplicate groups\n\n"
        msg += "Continue?"

        if not messagebox.askyesno("Auto-Delete", msg):
            return

        conn = self.db.get_connection()
        cursor = conn.cursor()

        total_deleted = 0

        for group in self.duplicate_groups:
            ids = group['ids'].split(',')

            # Keep first, delete rest
            for txn_id in ids[1:]:  # Skip first (index 0)
                cursor.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
                total_deleted += 1

        conn.commit()

        messagebox.showinfo(
            "Complete",
            f"Deleted {total_deleted} duplicate transaction(s)\n\n" +
            f"Kept {len(self.duplicate_groups)} original(s)"
        )

        self.dialog.destroy()
        self.callback()


def main():
    """Run the application"""
    root = tk.Tk()
    app = CashflowApp(root)

    # Force window to front and keep visible (Mac fix)
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    root.focus_force()

    root.mainloop()


if __name__ == "__main__":
    main()