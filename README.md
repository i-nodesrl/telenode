# About

This software has been developed by and for I-node s.r.l.

For more informations about what you're actually allowed to do with it, look at the [`LICENSE`](https://git.i-node.it/i-node/telenode/blob/master/LICENSE) file.

| Website | https&#x3A;// **[i-node.it](https://i-node.it)**           |
| :------ | :--------------------------------------------------------- |
| Wiki    | https&#x3A;// **[wiki.i-node.it](https://wiki.i-node.it)** |
| Git     | https&#x3A;// **[git.i-node.it](https://git.i-node.it)**   |

# Installation

Pretty straightforward:

```bash
cd /opt
git clone https://git.i-node.it/i-node/telenode.git
cd telenode
pip install telepot inotify
export ICINGA2_API_USER=APIUSER
export ICINGA2_API_PWD=F95S1VVQ67JSZHWD
export TELEGRAM_BOT_TOKEN=V1GMROGSCXLLTRMHQ7U0U1NBDUCYB7W6HSNBCCZ8BY2Y2
./telenode.py
```

## Update

You just have to update the code with the common `git pull` command.
If the script is in execution, you won't need to reload it as it's built to autorefresh itself if it receives any kind of modification.

## Commands

The bot is built to provide the following commands:

| Command      | Explaination                                                                  |
| :----------- | :---------------------------------------------------------------------------- |
| `/ping`      | Check if bot is listening and get its execution time                          |
| `/ack`       | Acknowledge object in alarm state                                             |
| `/status`    | Display detected and unacknowledged problem (and eventually its informations) |
| `/broadcast` | Send a broadcast message to bot subscribers                                   |

#### FAQs

1.  **`/broadcast` command is not working**

	Actually, `/broadcast` command is the only one which does not strictly rely on Telegram Bot APIs; in order to do that, APIs should provide a way to get Bot subscribers (which is not possible at the moment, at least using `telepot` bindings). That said, `telenode.py` will be looking for a `.users.json` file (in its path). If found, it'll parse it as a JSON object, obviously. The structure of the file should be as the following, basicly an array of `chat_id`s:

		[48386055,114706891,63223231]

### Contribution

If you want to contribute, head to our personal [Gitlab](https://git.i-node.it).
