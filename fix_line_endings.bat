@echo off
echo Fixing line endings in Git repository...
git config core.autocrlf false
git config core.eol lf
echo Creating .gitattributes file with LF settings...
echo "* text=auto eol=lf" > .gitattributes
echo "*.bat text eol=crlf" >> .gitattributes
echo "*.cmd text eol=crlf" >> .gitattributes
echo "*.ps1 text eol=crlf" >> .gitattributes
echo .gitattributes file created with LF line ending settings.
echo Done! You may need to reset your repository or re-checkout files to apply changes.
echo To reset: git rm --cached -r . && git reset --hard