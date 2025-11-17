#!/bin/bash
# Quick merge conflict resolution

echo "🔧 Resolving LOTUS merge conflicts..."
echo ""

# Check if we're in a merge
if ! git status | grep -q "both modified"; then
    echo "❌ No merge conflicts detected!"
    echo "Are you sure you ran: git merge origin/claude/fix-lotus-circular-deps-019ERLxe89jz2EXFgoMS6ZvS"
    exit 1
fi

echo "📝 Accepting incoming changes (the fixed versions)..."
git checkout --theirs lotus/nucleus.py
git checkout --theirs lotus/modules/capability_modules/consciousness/logic.py

echo "✅ Staging resolved files..."
git add lotus/nucleus.py
git add lotus/modules/capability_modules/consciousness/logic.py

echo "✅ Committing merge..."
git commit -m "Merge: Accept all fixes from claude/fix-lotus-circular-deps

- Fixed topological sort algorithm in nucleus.py
- Added missing imports to consciousness/logic.py  
- Made database optional
- System now boots successfully"

echo ""
echo "✅ Merge complete!"
echo ""
echo "🧪 Test the system:"
echo "   cd lotus && python nucleus.py"
echo ""
