import os
import random
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import googletrans
import wolframalpha
from io import BytesIO
from bs4 import BeautifulSoup
from gtts import gTTS
from views import Pagelist 
from .classes import IOBasedSource

class helper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name='translate', aliases=['trans', 'dich'])
    @app_commands.describe(
        dest="The language you want to translate to",
        text="The text you want to translate."
    )
    async def translate_command(self, ctx, dest, *, text: str):
        """
        Google translate anything.

        Gets the bot to translate text sentences to your desired language.
        """
        dest = dest.lower()
        if not dest in googletrans.LANGUAGES and not dest in googletrans.LANGCODES:
            dest = 'en'
        result = googletrans.Translator().translate(text=text, dest=dest)
        embed = discord.Embed(title="Translate results:",
                              color=ctx.author.color)
        embed.set_footer(
            text=f"Translated from {googletrans.LANGUAGES[result.src].upper()} to {googletrans.LANGUAGES[result.dest].upper()}.", icon_url=self.bot.user.display_avatar.url)
        embed.description = f"**Translated text: **```\n{result.text}\n```"
        if result.text != result.pronunciation:
            embed.description += f"**Pronunciation: **```\n{result.pronunciation}\n```"
        embed.set_author(name=f"{ctx.author} used ..translate",
                         icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name='read')
    @app_commands.describe(
        text='The text you want the bot to read.'
    )
    async def read_command(self, ctx: commands.Context, *, text=None):
        """
        Read something you type.

        Gets the bot to read text sentences you typed in a voice channel.
        """
        if not text:
            return await ctx.reply(embed=discord.Embed(description="**I don't know what to read.**"), mention_author=False)
        if ctx.author.voice is None:
            return await ctx.reply(embed=discord.Embed(description="**You are not currently in a voice channel.**"))
        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await voice_channel.connect()
        else:
            if not ctx.voice_client.is_playing():
                if not ctx.voice_client.channel == voice_channel:
                    await ctx.voice_client.move_to(voice_channel)
            else:
                if not ctx.voice_client.channel == voice_channel:
                    return await ctx.reply(embed=discord.Embed(description=f"**I'm already playing music in {ctx.voice_client.channel}**"), mention_author=False)

        reply = await ctx.reply(embed=discord.Embed(title="Processing the input"), mention_author=False)
        language = googletrans.Translator().detect(text).lang
        tts = gTTS(text=text, lang=language)
        file = BytesIO()
        tts.write_to_fp(file)
        file.seek(0)
        source = IOBasedSource(file.read(), pipe=True)
        file.close()
        await reply.edit(embed=discord.Embed(title="Finished processing"))
        ctx.voice_client.play(source)

    @commands.hybrid_command(name='findword', aliases=['we', 'find'])
    @app_commands.describe(
        letter='The letter those words start with.',
        page='The page contains the words.',
        syllables='The number of syllables of the words.'
    )
    async def findword_command(self, ctx, letter: str, page: int = None, syllables: int = None):
        """
        Finds a list of words.

        Gets the bot to find a list of English words that matches the condition on yougowords.com.
        """
        async def list_of_words(start: str, syllables: int = None, page: int = None, length: int = None):
            url = f"http://www.yougowords.com/start-with-{start}"
            if length:
                url += f"/{length}-letters"
            if syllables:
                url += f"/{syllables}-syllables"
            if page:
                url += f"-{page}"
            async with aiohttp.ClientSession() as session:
                response = await session.get(url=url)
                text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            try:
                info = soup.find('div', id="wordBody").find('p').find('strong')
            except AttributeError:
                return None
            return info
        information = await list_of_words(letter, syllables, page)
        embed = discord.Embed(title="Words found...")
        embed.set_author(icon_url=self.bot.user.display_avatar.url,
                         name=f"Words that start with {letter}")
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f"Requested by {ctx.author}")
        if information != None:
            info = information.next_sibling
            embed.description = f"```\n{info}\n```"
        else:
            embed.description = f"```\nNothing found.\n```"
        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name='dictionary', aliases=['dict'])
    @app_commands.describe(
        word='The word to find the definition'
    )
    async def dictionary_command(self, ctx, *, word):
        """
        Looks up the Engish dictionary.

        Finds the phonetics, origins and definitions of a word for you.
        """
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
            response = await response.json()
        if "title" in response:
            embed = discord.Embed(title=f"Finding definition for {word}...")
            embed.set_author(icon_url=self.bot.user.display_avatar.url,
                             name=f"Looking up the dictionary...")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text=f"Requested by {ctx.author}")
            embed.description = "```\nNo definitions found.\n```"
            return await ctx.reply(embed=embed, mention_author=False)
        embedlist = []
        length = len(response)
        for i, word in enumerate(response):
            embed = discord.Embed(title=f"WORD:   *{word['word'].upper()}*\n")
            embed.set_author(
                icon_url=self.bot.user.display_avatar.url, name=f"Page {i+1}/{length}...")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text=f"Requested by {ctx.author}")
            meanings = ""
            for meaning in word['meanings']:
                meanings += "```\n"
                if "partOfSpeech" in meaning:
                    meanings += f"Part of speech: {meaning['partOfSpeech']}\n"
                meanings += "Definitions: \n"
                for definition in meaning['definitions']:
                    if "definition" in definition:
                        meanings += f"{i}. Definition: {definition['definition']}\n"
                    if "example" in definition:
                        meanings += f"   Example: {definition['example']}\n"
                    if "synonyms" in definition and len(definition['synonyms']) > 0:
                        meanings += f"   Synonyms: {', '.join(definition['synonyms'])}\n"
                    if "antonyms" in definition and len(definition['antonyms']) > 0:
                        meanings += f"   Antonyms: {', '.join(definition['antonyms'])}\n"
                meanings += "```"
            field_text = ""
            phonetics = ""
            for phonetic in word['phonetics']:
                if "text" in phonetic:
                    phonetics += f"```\n{phonetic['text']}\n```"
            if phonetics:
                field_text += f"***Phonetics:*** {phonetics}\n"
            if "origin" in word:
                field_text += f"***Origin:*** ```\n{word['origin']}\n```"
            field_text += f"\n***Meanings:*** {meanings}"
            embed.description = field_text
            embedlist.append(embed)
        if length <= 1:
            return await ctx.reply(embed=embedlist[0], mention_author=False)
        view = Pagelist(embedlist, timeout=180)
        message = await ctx.reply(embed=embedlist[0], view=view, mention_author=False)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name='question', aliases=['ques'])
    @app_commands.describe(
        question='The question to answer'
    )
    async def question_command(self, ctx, *, question):
        """
        Asks the bot a question.

        It will try its best to answer you.
        """
        app_id = os.getenv('WAAID')
        client = wolframalpha.Client(app_id=app_id)
        res = client.query(input=question, units='metric')
        file = discord.File("assets//images//answerbox.jpg")
        try:
            answer = next(res.results).text
        except:
            embed = discord.Embed(
                title="Answer: ", description=f"**No answer was found**", color=ctx.author.color)
            embed.set_author(name="Question: " + question,
                             icon_url=self.bot.user.display_avatar.url)
            embed.set_thumbnail(url="attachment://answerbox.jpg")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text="Asked by {}".format(ctx.author))
            return await ctx.reply(embed=embed, file=file, mention_author=False)
        if answer == 'None':
            embed = discord.Embed(
                title="Answer: ", description=f"**No answer was found**", color=ctx.author.color)
            embed.set_author(name="Question: " + question,
                             icon_url=self.bot.user.display_avatar.url)
            embed.set_thumbnail(url="attachment://answerbox.jpg")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text="Asked by {}".format(ctx.author))
        else:
            embed = discord.Embed(
                title="Answer: ", description=f"**{answer}**", color=ctx.author.color)
            embed.set_author(name="Question: " + question,
                             icon_url=self.bot.user.display_avatar.url)
            file = discord.File("Images//answerbox.jpg")
            embed.set_thumbnail(url="attachment://answerbox.jpg")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text="Asked by {}".format(ctx.author))
        await ctx.reply(embed=embed, file=file, mention_author=False)

    @commands.hybrid_command(name="ping")
    async def ping_command(self, ctx):
        """
        Shows the ping of the bot.

        Shows the current latency of the bot.
        """
        return await ctx.reply(embed=discord.Embed(title=f"The latency is {self.bot.latency*1000:.2f}ms.", color=ctx.author.color), mention_author=False)

    @commands.hybrid_command(name='answer', aliases=['ans', 'answerme'])
    @app_commands.describe(
        question='The question to answer'
    )
    async def answer_command(self, ctx, *, question):
        """
        Answer a yes/no question of yours.

        The bot will try its best to find the answer yes or no to your question.

        Attributes:
            <question> : The question to answer.
        """
        answers = ["I don't know",
                   "I don't have a reply",
                   "Certainly",
                   "Absolutely",
                   "Yes, I think so",
                   "No, of course not",
                   "Yes.",
                   "No.",
                   "Without a doubt.",
                   "As far as I know, yes!",
                   "As far as I know, no!"]
        answer = f'Answer: {random.choice(answers)}'
        embed = discord.Embed(color=ctx.author.color)
        embed.description = f'Question: **{question}**\n\u200b'
        file = discord.File("assets//images//answerbox.jpg")
        embed.set_thumbnail(url="attachment://answerbox.jpg")
        embed.set_author(name=f'{ctx.author.display_name} used ..question.',
                         icon_url=self.bot.user.display_avatar.url)
        embed.add_field(name=f'_{answer}_', value='\u200b')
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f'Requested by {ctx.author}')
        await ctx.reply(file=file, embed=embed, mention_author=False)

    @commands.hybrid_command(aliases=['yn'])
    @app_commands.describe(
        question='The decision you want to make.'
    )
    async def yesorno(self, ctx, *, question=None):
        """
        Helps you make a decision
        
        Gods will find the correct decision for you.

        Attributes: None.
        """
        response = ['Yes.', 'No.']
        embed = discord.Embed(
            title=f'_Answer:_ **{random.choice(response)}**', color=ctx.author.color)
        embed.set_author(name='YES or NO?')
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f'Requested by {ctx.author}')
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(helper(bot))
