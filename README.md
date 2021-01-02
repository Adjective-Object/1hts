# 1hts

Some tools to help with one-handed typing.

## Background

Because of medical reasons, I have limited use of my right hand for several months. After trying to use [xhk](https://github.com/kbingham/xhk) for a week, I wanted a separate modifier key rather than using the space bar.

I found Koolertron manufacturing [one handed keyboards](http://www.koolertron.com/koolertron-cherry-mx-red-programmable-gaming-keypad-for-pubg-mechanical-gaming-keyboard-with-43-programmable-keys-for-playerunknowns-battlegrounds-singlehanded-keypad-macro-setting-p-818.html) that are currently marketed for gaming. They have enough spare keys to support halfquerty and some modifier keys. It self describes as "LingYao ShangHai Thumb Keyboard" in the device name, and marketed under the company name "Koolertron". I'm unsure if Cypress is changing its name, if it has subsidiaries, or if other people are passing around their firmware without updating the vendor info.

This repo is for some tools to help deal with this set up.

## Multi-Layer Aliasing

```
pipenv run python layeralias
```

When typing across layers, releasing the layer key without releasing the modified key causes a keypress to be emitted for both the modified layer and the base layer. `layeralias` reads the Koolertron keymap, detects aliasing sequences, and emits backspaces to correct the aliasing.
