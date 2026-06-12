browser-setup:
  npx agent-browser install

browser url:
  npx agent-browser open {{url}}

# Browser checks assume the app is already running through the project's
# run-app target, commonly `just dev [port]`.

# In Node projects that add agent-browser to devDependencies, prefer:
# browser-setup:
#   npm exec -- agent-browser install
#
# browser url:
#   npm exec -- agent-browser open {{url}}
