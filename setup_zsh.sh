#!/bin/bash
# Setup zsh with oh-my-zsh and plugins

set -e

echo "🔧 Installing zsh..."
sudo apt-get update
sudo apt-get install -y zsh git curl

echo "✅ zsh installed: $(which zsh)"
echo ""

echo "📦 Installing oh-my-zsh..."
# Install oh-my-zsh (unattended)
RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

echo "✅ oh-my-zsh installed"
echo ""

echo "🔌 Installing zsh-autosuggestions..."
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

echo "✅ zsh-autosuggestions cloned"
echo ""

echo "⚙️  Configuring .zshrc..."
# Backup existing .zshrc if it exists
if [ -f ~/.zshrc ]; then
    cp ~/.zshrc ~/.zshrc.backup.$(date +%s)
    echo "📋 Backed up existing .zshrc"
fi

# Update plugins in .zshrc
if grep -q "^plugins=" ~/.zshrc 2>/dev/null; then
    # Replace existing plugins line
    sed -i 's/^plugins=.*/plugins=(git zsh-autosuggestions)/' ~/.zshrc
else
    # Add plugins line if it doesn't exist
    echo "plugins=(git zsh-autosuggestions)" >> ~/.zshrc
fi

echo "✅ Configured plugins in .zshrc"
echo ""

echo "🔄 Changing default shell to zsh..."
sudo chsh -s $(which zsh) $USER

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Log out and log back in (or run: exec zsh)"
echo "   2. Enjoy zsh with autosuggestions!"
echo ""
echo "💡 Tip: Autosuggestions appear in gray as you type."
echo "   Press → (right arrow) to accept a suggestion"

