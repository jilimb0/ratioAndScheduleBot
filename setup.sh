#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Установка Telegram Bot для управления распорядком дня${NC}"
echo "======================================================"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установите Python 3.8+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python найден${NC}"

# Проверка pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 не найден. Установите pip${NC}"
    exit 1
fi

echo -e "${GREEN}✅ pip найден${NC}"

# Создание виртуального окружения
echo -e "${YELLOW}📦 Создание виртуального окружения...${NC}"
python3 -m venv venv

# Активация виртуального окружения
echo -e "${YELLOW}🔄 Активация виртуального окружения...${NC}"
source venv/bin/activate

# Установка зависимостей
echo -e "${YELLOW}📥 Установка зависимостей...${NC}"
pip install -r requirements.txt

# Проверка наличия файла .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️ Создание файла конфигурации...${NC}"
    cp .env.example .env 2>/dev/null || cat > .env << EOF
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TIMEZONE=UTC
PORT=8000
USE_WEBHOOK=false
WEBHOOK_URL=
EOF
    
    echo -e "${YELLOW}📝 Необходимо настроить BOT_TOKEN в файле .env${NC}"
    echo -e "${YELLOW}   1. Перейдите к @BotFather в Telegram${NC}"
    echo -e "${YELLOW}   2. Создайте нового бота командой /newbot${NC}"
    echo -e "${YELLOW}   3. Скопируйте токен и вставьте в .env файл${NC}"
    echo ""
    
    # Запрос токена бота
    read -p "Введите токен вашего бота (или нажмите Enter для пропуска): " bot_token
    
    if [ ! -z "$bot_token" ]; then
        sed -i.bak "s/YOUR_BOT_TOKEN_HERE/$bot_token/" .env
        echo -e "${GREEN}✅ Токен бота сохранен${NC}"
    fi
fi

# Создание базы данных
echo -e "${YELLOW}🗄️ Инициализация базы данных...${NC}"
python3 -c "from database import init_db; init_db()"

echo ""
echo -e "${GREEN}🎉 Установка завершена!${NC}"
echo ""
echo -e "${GREEN}Для запуска бота используйте:${NC}"
echo -e "${YELLOW}  source venv/bin/activate${NC}"
echo -e "${YELLOW}  python main.py${NC}"
echo ""
echo -e "${GREEN}Или используйте скрипт запуска:${NC}"
echo -e "${YELLOW}  ./run.sh${NC}"
echo ""

# Создание скрипта запуска
cat > run.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python main.py
EOF

chmod +x run.sh

echo -e "${GREEN}📋 Доступные команды бота:${NC}"
echo "  /start - Запуск бота"
echo "  /статус - Текущий статус задач"
echo "  /отчёт - Отчёт за последние дни"
echo "  /расписание - Показать расписание"
echo ""
echo -e "${GREEN}📖 Подробная документация в README.md${NC}"