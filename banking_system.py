import sqlite3
import datetime
from abc import ABC, abstractmethod
import hashlib

class Bank:
    """Main Bank Management System"""
    
    def __init__(self, db_name="bank.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                created_date TEXT
            )
        ''')
        
        # Accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_date TEXT,
                status TEXT DEFAULT 'Active',
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account_id INTEGER,
                to_account_id INTEGER,
                amount REAL NOT NULL,
                transaction_type TEXT,
                timestamp TEXT,
                description TEXT,
                FOREIGN KEY (from_account_id) REFERENCES accounts(account_id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(account_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_name)
    
    def create_customer(self, name, email, phone, address):
        """Create new customer"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO customers (name, email, phone, address, created_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, phone, address, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            customer_id = cursor.lastrowid
            return customer_id, "Customer created successfully"
        except sqlite3.IntegrityError:
            return None, "Email already exists"
        finally:
            conn.close()
    
    def create_account(self, customer_id, account_type, initial_balance=0):
        """Create new account for customer"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO accounts (customer_id, account_type, balance, created_date)
            VALUES (?, ?, ?, ?)
        ''', (customer_id, account_type, initial_balance, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        account_id = cursor.lastrowid
        conn.close()
        
        return account_id, "Account created successfully"
    
    def deposit(self, account_id, amount):
        """Deposit money to account"""
        if amount <= 0:
            return False, "Amount must be positive"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT balance FROM accounts WHERE account_id = ?', (account_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Account not found"
            
            new_balance = result[0] + amount
            
            cursor.execute('UPDATE accounts SET balance = ? WHERE account_id = ?', 
                         (new_balance, account_id))
            
            cursor.execute('''
                INSERT INTO transactions (from_account_id, to_account_id, amount, 
                                         transaction_type, timestamp, description)
                VALUES (NULL, ?, ?, ?, ?, ?)
            ''', (account_id, amount, 'DEPOSIT', 
                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Cash Deposit'))
            
            conn.commit()
            return True, f"Deposited ₹{amount}. New balance: ₹{new_balance}"
        finally:
            conn.close()
    
    def withdraw(self, account_id, amount):
        """Withdraw money from account"""
        if amount <= 0:
            return False, "Amount must be positive"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT balance FROM accounts WHERE account_id = ?', (account_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Account not found"
            
            if result[0] < amount:
                return False, "Insufficient balance"
            
            new_balance = result[0] - amount
            
            cursor.execute('UPDATE accounts SET balance = ? WHERE account_id = ?', 
                         (new_balance, account_id))
            
            cursor.execute('''
                INSERT INTO transactions (from_account_id, to_account_id, amount, 
                                         transaction_type, timestamp, description)
                VALUES (?, NULL, ?, ?, ?, ?)
            ''', (account_id, amount, 'WITHDRAWAL', 
                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Cash Withdrawal'))
            
            conn.commit()
            return True, f"Withdrawn ₹{amount}. Remaining balance: ₹{new_balance}"
        finally:
            conn.close()
    
    def transfer(self, from_account_id, to_account_id, amount):
        """Transfer money between accounts"""
        if amount <= 0:
            return False, "Amount must be positive"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT balance FROM accounts WHERE account_id = ?', (from_account_id,))
            from_balance = cursor.fetchone()
            
            if not from_balance:
                return False, "Source account not found"
            
            if from_balance[0] < amount:
                return False, "Insufficient balance"
            
            cursor.execute('SELECT balance FROM accounts WHERE account_id = ?', (to_account_id,))
            to_balance = cursor.fetchone()
            
            if not to_balance:
                return False, "Destination account not found"
            
            # Deduct from source
            new_from_balance = from_balance[0] - amount
            cursor.execute('UPDATE accounts SET balance = ? WHERE account_id = ?', 
                         (new_from_balance, from_account_id))
            
            # Add to destination
            new_to_balance = to_balance[0] + amount
            cursor.execute('UPDATE accounts SET balance = ? WHERE account_id = ?', 
                         (new_to_balance, to_account_id))
            
            # Record transaction
            cursor.execute('''
                INSERT INTO transactions (from_account_id, to_account_id, amount, 
                                         transaction_type, timestamp, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (from_account_id, to_account_id, amount, 'TRANSFER', 
                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Account Transfer'))
            
            conn.commit()
            return True, f"Transferred ₹{amount} successfully"
        finally:
            conn.close()
    
    def get_balance(self, account_id):
        """Get account balance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT balance FROM accounts WHERE account_id = ?', (account_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
    
    def get_transaction_history(self, account_id, limit=10):
        """Get transaction history for account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT transaction_id, amount, transaction_type, timestamp, description
            FROM transactions
            WHERE from_account_id = ? OR to_account_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (account_id, account_id, limit))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return transactions
    
    def get_customer_accounts(self, customer_id):
        """Get all accounts for a customer"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT account_id, account_type, balance, status
            FROM accounts
            WHERE customer_id = ?
        ''', (customer_id,))
        
        accounts = cursor.fetchall()
        conn.close()
        
        return accounts


class BankingApp:
    """CLI Interface for Banking System"""
    
    def __init__(self):
        self.bank = Bank()
        self.current_customer = None
        self.current_account = None
    
    def main_menu(self):
        """Main menu loop"""
        while True:
            print("\n" + "="*50)
            print("🏦 BANKING MANAGEMENT SYSTEM 🏦".center(50))
            print("="*50)
            print("\n1. Create New Customer")
            print("2. Create Account")
            print("3. Deposit Money")
            print("4. Withdraw Money")
            print("5. Transfer Money")
            print("6. Check Balance")
            print("7. View Transaction History")
            print("8. Exit")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == '1':
                self.create_customer()
            elif choice == '2':
                self.create_account()
            elif choice == '3':
                self.deposit_money()
            elif choice == '4':
                self.withdraw_money()
            elif choice == '5':
                self.transfer_money()
            elif choice == '6':
                self.check_balance()
            elif choice == '7':
                self.view_history()
            elif choice == '8':
                print("\nThank you for using Banking System!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    def create_customer(self):
        """Create new customer"""
        print("\n--- CREATE NEW CUSTOMER ---")
        name = input("Enter customer name: ").strip()
        email = input("Enter email: ").strip()
        phone = input("Enter phone number: ").strip()
        address = input("Enter address: ").strip()
        
        customer_id, message = self.bank.create_customer(name, email, phone, address)
        
        if customer_id:
            print(f"✅ {message}")
            print(f"Customer ID: {customer_id}")
            self.current_customer = customer_id
        else:
            print(f"❌ {message}")
    
    def create_account(self):
        """Create new account"""
        if not self.current_customer:
            customer_id = input("Enter customer ID: ").strip()
            try:
                self.current_customer = int(customer_id)
            except:
                print("❌ Invalid customer ID")
                return
        
        print("\n--- CREATE NEW ACCOUNT ---")
        print("Account Types: Savings, Checking, Business")
        account_type = input("Enter account type: ").strip()
        initial_balance = input("Enter initial balance (or 0): ").strip()
        
        try:
            initial_balance = float(initial_balance)
        except:
            initial_balance = 0
        
        account_id, message = self.bank.create_account(self.current_customer, account_type, initial_balance)
        print(f"✅ {message}")
        print(f"Account ID: {account_id}")
        self.current_account = account_id
    
    def deposit_money(self):
        """Deposit money"""
        if not self.current_account:
            account_id = input("Enter account ID: ").strip()
            try:
                self.current_account = int(account_id)
            except:
                print("❌ Invalid account ID")
                return
        
        amount = input("Enter amount to deposit: ₹").strip()
        
        try:
            amount = float(amount)
            success, message = self.bank.deposit(self.current_account, amount)
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        except:
            print("❌ Invalid amount")
    
    def withdraw_money(self):
        """Withdraw money"""
        if not self.current_account:
            account_id = input("Enter account ID: ").strip()
            try:
                self.current_account = int(account_id)
            except:
                print("❌ Invalid account ID")
                return
        
        amount = input("Enter amount to withdraw: ₹").strip()
        
        try:
            amount = float(amount)
            success, message = self.bank.withdraw(self.current_account, amount)
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        except:
            print("❌ Invalid amount")
    
    def transfer_money(self):
        """Transfer between accounts"""
        print("\n--- FUND TRANSFER ---")
        from_id = input("Enter source account ID: ").strip()
        to_id = input("Enter destination account ID: ").strip()
        amount = input("Enter amount: ₹").strip()
        
        try:
            from_id = int(from_id)
            to_id = int(to_id)
            amount = float(amount)
            
            success, message = self.bank.transfer(from_id, to_id, amount)
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        except:
            print("❌ Invalid input")
    
    def check_balance(self):
        """Check account balance"""
        if not self.current_account:
            account_id = input("Enter account ID: ").strip()
            try:
                self.current_account = int(account_id)
            except:
                print("❌ Invalid account ID")
                return
        
        balance = self.bank.get_balance(self.current_account)
        
        if balance is not None:
            print(f"\n💰 Account Balance: ₹{balance:.2f}")
        else:
            print("❌ Account not found")
    
    def view_history(self):
        """View transaction history"""
        if not self.current_account:
            account_id = input("Enter account ID: ").strip()
            try:
                self.current_account = int(account_id)
            except:
                print("❌ Invalid account ID")
                return
        
        transactions = self.bank.get_transaction_history(self.current_account)
        
        if transactions:
            print("\n--- TRANSACTION HISTORY ---")
            print(f"{'ID':<5} {'Type':<12} {'Amount':<10} {'Date':<20}")
            print("-" * 50)
            for trans in transactions:
                print(f"{trans[0]:<5} {trans[2]:<12} ₹{trans[1]:<9.2f} {trans[3]:<20}")
        else:
            print("❌ No transactions found")


if __name__ == "__main__":
    app = BankingApp()
    app.main_menu()
