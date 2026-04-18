import discord
from discord import app_commands 
from discord.ext import commands
import os
import sys
import asyncio
import json

# =========================================================
# 1. 봇 기본 설정
# =========================================================
intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  

bot = commands.Bot(command_prefix='!', intents=intents)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

ALLOWED_USERS = [343290913172226049] 
processing_users = set()

# =========================================================
# 2. 내부 함수
# =========================================================
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[저장완료] 설정이 저장되었습니다.")

def migrate_data(data, guild_id):
    if guild_id not in data:
        data[guild_id] = {}
    if not isinstance(data[guild_id], dict):
        data[guild_id] = {}
    if "channels" in data[guild_id]:
        new_channels = {}
        for name, content in data[guild_id]["channels"].items():
            if isinstance(content, str):
                new_channels[name] = {"msg": content}
            else:
                new_channels[name] = content
        data[guild_id]["channels"] = new_channels
    return data

async def channel_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    data = load_settings()
    guild_id = str(interaction.guild_id)
    if guild_id not in data or "channels" not in data[guild_id]:
        return []
    templates = list(data[guild_id]["channels"].keys())
    return [app_commands.Choice(name=name, value=name) for name in templates if current.lower() in name.lower()][:25]

async def reorder_channels_in_category(category, template_keys):
    for correct_index, ch_name in enumerate(template_keys):
        channel = discord.utils.get(category.text_channels, name=ch_name)
        if channel:
            if channel.position != correct_index:
                try: await channel.edit(position=correct_index)
                except: pass
    await asyncio.sleep(0.5)

async def create_single_channel_in_category(guild, category, ch_name, info, member, position=None, should_tag=False):
    if discord.utils.get(category.text_channels, name=ch_name):
        return False

    msg = info.get("msg", "")
    role_id = info.get("role_id")

    if position is not None:
        new_ch = await category.create_text_channel(name=ch_name, position=position)
    else:
        new_ch = await category.create_text_channel(name=ch_name)
    
    if role_id:
        view_role = guild.get_role(role_id)
        if view_role:
            await new_ch.set_permissions(view_role, read_messages=True, send_messages=True)

    if msg:
        embed = discord.Embed(title=f"{ch_name}", description=msg, color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        if should_tag:
            await new_ch.send(content=member.mention, embed=embed)
        else:
            await new_ch.send(embed=embed)
    
    return True

async def create_user_room(guild, member):
    guild_id = str(guild.id)
    data = load_settings()
    data = migrate_data(data, guild_id)

    if "channels" not in data[guild_id] or not data[guild_id]["channels"]:
        return False, "설정된 채널 템플릿이 없습니다."

    target_category = discord.utils.get(guild.categories, name=str(member.display_name))
    
    if not target_category:
        for category in guild.categories:
            if category.name and str(member.display_name).startswith(category.name):
                target_category = category
                break 

    if target_category:
        await target_category.set_permissions(member, read_messages=True, send_messages=True)
        return True, f"'{target_category.name}' 그룹에 멤버로 추가되었습니다."
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
        }
        target_category = await guild.create_category(name=str(member.display_name), overwrites=overwrites)
        
        template_keys = list(data[guild_id]["channels"].keys())
        for i, (ch_name, info) in enumerate(data[guild_id]["channels"].items()):
            do_tag = (i == 0)
            await create_single_channel_in_category(guild, target_category, ch_name, info, member, position=i, should_tag=do_tag)
            await asyncio.sleep(0.5)
        
        await reorder_channels_in_category(target_category, template_keys)
        return True, f"새로운 카테고리 '{target_category.name}'가 생성되었습니다."

# =========================================================
# 3. 봇 이벤트
# =========================================================
@bot.event
async def on_ready():
    print(f'---------------------------------------')
    print(f'로그인 성공: {bot.user}')
    print(f'설정 파일 위치: {SETTINGS_FILE}')
    print(f'---------------------------------------')

@bot.command()
async def 동기화(ctx):
    if ctx.author.id in ALLOWED_USERS:
        await bot.tree.sync()
        await ctx.send("✅ 슬래시 커맨드 동기화 완료!")
    else:
        await ctx.send("❌ 관리자만 동기화할 수 있습니다.")

@bot.event
async def on_member_join(member):
    if member.id in processing_users:
        return
    processing_users.add(member.id)
    try:
        guild = member.guild
        guild_id = str(guild.id)
        data = load_settings()
        data = migrate_data(data, guild_id)
        if "auto_role" in data[guild_id]:
            role_id = data[guild_id]["auto_role"]
            role = guild.get_role(role_id)
            if role:
                try: await member.add_roles(role)
                except: pass
        await create_user_room(guild, member)
    except Exception as e:
        print(f"오류: {e}")
    finally:
        if member.id in processing_users:
            processing_users.remove(member.id)

# =========================================================
# 4. 슬래시 커맨드
# =========================================================

# (1) [핵심] 채널 이름 일괄 변경 (서버 전체 적용)
@bot.tree.command(name="채널이름변경", description="서버에 있는 모든 특정 이름의 채널을 찾아 새로운 이름으로 바꿉니다.")
@app_commands.describe(old_name="현재 채널 이름 (바꿀 대상)", new_name="새로운 채널 이름")
@app_commands.autocomplete(old_name=channel_name_autocomplete)
@app_commands.default_permissions(administrator=True)
async def rename_channel_bulk(interaction: discord.Interaction, old_name: str, new_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    guild_id = str(guild.id)
    data = load_settings()
    data = migrate_data(data, guild_id)

    # 1. 템플릿(설정파일)도 같이 업데이트 (그래야 나중에 들어올 사람도 새 이름을 씀)
    # (이 부분이 없으면 나중에 들어온 사람은 옛날 이름으로 만들어져서 꼬입니다!)
    if "channels" in data[guild_id] and old_name in data[guild_id]["channels"]:
        current_channels = data[guild_id]["channels"]
        new_channels_dict = {}
        
        for key, val in current_channels.items():
            if key == old_name:
                new_channels_dict[new_name] = val # 키 변경
            else:
                new_channels_dict[key] = val
        
        data[guild_id]["channels"] = new_channels_dict
        save_settings(data)
        print(f"[설정업데이트] 템플릿 이름 변경: {old_name} -> {new_name}")

    # 2. [진짜 핵심] 서버에 깔려있는 실제 채널들 이름 바꾸기
    await interaction.followup.send(f"🚀 **서버 전체 스캔 시작!**\n모든 카테고리에서 **`{old_name}`** 채널을 찾아 **`{new_name}`**(으)로 변경합니다...")
    
    rename_count = 0
    # 모든 카테고리를 순회
    for category in guild.categories:
        # 그 카테고리 안에 'old_name'을 가진 채널이 있는지 찾음
        target_channel = discord.utils.get(category.text_channels, name=old_name)
        
        if target_channel:
            try:
                # 찾았으면 이름 변경!
                await target_channel.edit(name=new_name)
                rename_count += 1
                await asyncio.sleep(1) # 디스코드 부하 방지 (1초 대기)
            except Exception as e:
                print(f"[변경실패] {target_channel.name}: {e}")

    await interaction.followup.send(f"✨ **작업 완료!**\n총 **{rename_count}**개의 채널 이름을 **`{new_name}`**(으)로 바꿨습니다.")

# (2) 템플릿 수정
@bot.tree.command(name="템플릿수정", description="템플릿 내용/권한 수정")
@app_commands.describe(channel_name="수정할 템플릿", message="새 메시지", view_role="새 열람 역할")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def modify_channel_template(interaction: discord.Interaction, channel_name: str, message: str = None, view_role: discord.Role = None):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)
    
    if "channels" not in data[guild_id] or channel_name not in data[guild_id]["channels"]:
        await interaction.followup.send(f"⚠️ `{channel_name}` 템플릿이 없습니다.")
        return
    
    entry = data[guild_id]["channels"][channel_name]
    result_msg = f"🔄 **수정 완료!**\n📂 대상: `{channel_name}`"
    
    if message:
        entry["msg"] = message.replace("\\n", "\n")
        result_msg += "\n📝 메시지 업데이트됨"
    if view_role:
        entry["role_id"] = view_role.id
        result_msg += f"\n🔒 권한: {view_role.mention}"
            
    data[guild_id]["channels"][channel_name] = entry
    save_settings(data)
    await interaction.followup.send(result_msg)

# (3) 채널 추가 배포
@bot.tree.command(name="채널추가배포", description="새로 만든 템플릿 채널을 기존 방들에 일괄 생성합니다.")
@app_commands.describe(channel_name="배포할 채널 이름")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def distribute_new_channel(interaction: discord.Interaction, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    guild_id = str(guild.id)
    data = load_settings()
    data = migrate_data(data, guild_id)

    if "channels" not in data[guild_id] or channel_name not in data[guild_id]["channels"]:
        await interaction.followup.send(f"⚠️ **`{channel_name}`** 템플릿이 없습니다.")
        return
    
    info = data[guild_id]["channels"][channel_name]
    template_keys = list(data[guild_id]["channels"].keys())
    try: target_index = template_keys.index(channel_name)
    except ValueError: target_index = None
    do_tag = (target_index == 0)

    await interaction.followup.send(f"🚀 **`{channel_name}`** (위치: {target_index+1}번째) 배포 시작...")
    
    success_count = 0
    for member in guild.members:
        if member.bot: continue

        target_category = discord.utils.get(guild.categories, name=str(member.display_name))
        if not target_category:
            for category in guild.categories:
                if category.name and str(member.display_name).startswith(category.name):
                    target_category = category
                    break
        
        if target_category:
            created = await create_single_channel_in_category(guild, target_category, channel_name, info, member, position=target_index, should_tag=do_tag)
            await reorder_channels_in_category(target_category, template_keys)
            if created:
                success_count += 1
                
    await interaction.followup.send(f"✅ **배포 완료!**\n총 **{success_count}**개의 카테고리에 작업되었습니다.")

# (4) 공지 수정
@bot.tree.command(name="공지수정", description="템플릿 내용으로 기존 공지를 수정합니다.")
@app_commands.describe(channel_name="수정할 채널 이름")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def edit_announcement(interaction: discord.Interaction, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    guild_id = str(guild.id)
    data = load_settings()
    data = migrate_data(data, guild_id)
    
    if "channels" not in data[guild_id] or channel_name not in data[guild_id]["channels"]:
        await interaction.followup.send(f"⚠️ 설정 없음.")
        return
    
    info = data[guild_id]["channels"][channel_name]
    new_msg = info.get("msg", "")
    
    if not new_msg:
        await interaction.followup.send(f"⚠️ 내용 없음.")
        return

    await interaction.followup.send(f"✏️ 수정 중...")
    success_count = 0
    create_count = 0
    for category in guild.categories:
        for channel in category.text_channels:
            if channel_name in channel.name:
                try:
                    new_embed = discord.Embed(title=f"{channel_name}", description=new_msg, color=discord.Color.green())
                    new_embed.set_footer(text="내용이 수정되었습니다.")
                    target_msg = None
                    async for msg in channel.history(limit=10):
                        if msg.author == bot.user:
                            target_msg = msg
                            break
                    if target_msg:
                        await target_msg.edit(embed=new_embed)
                        success_count += 1
                    else:
                        await channel.send(embed=new_embed)
                        create_count += 1
                    await asyncio.sleep(0.5)
                except: pass

    await interaction.followup.send(f"✅ **완료!** (수정: {success_count} / 신규: {create_count})")

# (5) 템플릿 순서
@bot.tree.command(name="템플릿순서", description="채널 생성 순서를 변경합니다.")
@app_commands.describe(channel_name="채널 이름", order="몇 번째로 (1부터)")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def reorder_template(interaction: discord.Interaction, channel_name: str, order: int):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)

    if "channels" not in data[guild_id] or channel_name not in data[guild_id]["channels"]:
        await interaction.followup.send(f"⚠️ `{channel_name}` 없음.")
        return
    
    current_channels = data[guild_id]["channels"]
    keys = list(current_channels.keys())
    
    if order < 1: order = 1
    if order > len(keys): order = len(keys)
    
    keys.remove(channel_name)
    keys.insert(order - 1, channel_name)
    
    new_channels = {k: current_channels[k] for k in keys}
    data[guild_id]["channels"] = new_channels
    save_settings(data)
    
    desc = ""
    for i, name in enumerate(keys):
        desc += f"**{i+1}번:** {name}\n"
    await interaction.followup.send(f"✅ **순서 변경 완료!**\n\n{desc}")

# (6) 메시지 일괄 전송
@bot.tree.command(name="메시지일괄전송", description="메시지 전송")
@app_commands.describe(channel_name="보낼 채널 이름")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def send_batch_message(interaction: discord.Interaction, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    guild_id = str(guild.id)
    data = load_settings()
    data = migrate_data(data, guild_id)
    
    if "channels" not in data[guild_id] or channel_name not in data[guild_id]["channels"]:
        await interaction.followup.send(f"⚠️ 설정 없음")
        return
    
    info = data[guild_id]["channels"][channel_name]
    msg = info.get("msg", "")
    
    if not msg:
        await interaction.followup.send(f"⚠️ 메시지 없음")
        return

    await interaction.followup.send(f"🚀 전송 시작...")
    count = 0
    for category in guild.categories:
        for channel in category.text_channels:
            if channel_name in channel.name:
                try:
                    embed = discord.Embed(title=f"{channel_name}", description=msg, color=discord.Color.green())
                    embed.set_footer(text="관리자 일괄 전송")
                    await channel.send(embed=embed)
                    count += 1
                    await asyncio.sleep(1) 
                except: pass
    await interaction.followup.send(f"✅ **{count}**개 전송 완료")

# (7) 템플릿 생성
@bot.tree.command(name="템플릿생성", description="템플릿 추가")
async def set_channel_template(interaction: discord.Interaction, channel_name: str, message: str, view_role: discord.Role = None):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)
    if "channels" not in data[guild_id]: data[guild_id]["channels"] = {}
    
    entry = {"msg": message.replace("\\n", "\n")}
    role_info = ""
    if view_role:
        entry["role_id"] = view_role.id
        role_info = f" (+ {view_role.mention})"
    
    data[guild_id]["channels"][channel_name] = entry
    save_settings(data)
    await interaction.followup.send(f"✅ 저장: `{channel_name}`{role_info}")

# (8) 템플릿 삭제
@bot.tree.command(name="템플릿삭제", description="템플릿 삭제")
@app_commands.describe(channel_name="삭제할 채널")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def remove_channel_template(interaction: discord.Interaction, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    if "channels" in data[guild_id] and channel_name in data[guild_id]["channels"]:
        del data[guild_id]["channels"][channel_name]
        save_settings(data)
        await interaction.followup.send(f"🗑️ 삭제 완료")
    else:
        await interaction.followup.send(f"⚠️ 없음")

# (9) 템플릿 목록
@bot.tree.command(name="템플릿목록", description="템플릿 확인")
async def list_channel_templates(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)
    if "channels" in data[guild_id] and data[guild_id]["channels"]:
        desc = ""
        for i, (name, info) in enumerate(data[guild_id]["channels"].items()):
            msg = info.get("msg", "") if isinstance(info, dict) else info
            role_str = ""
            if isinstance(info, dict) and "role_id" in info:
                role = interaction.guild.get_role(info["role_id"])
                if role: role_str = f" [🔒{role.name}]"
            desc += f"**{i+1}. {name}**{role_str}: {msg[:15]}...\n"
        embed = discord.Embed(title="📋 템플릿 목록 (생성 순서)", description=desc, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("📭 없음")

# (10) 기타 명령어들
@bot.tree.command(name="채널생성", description="수동 채널 생성")
async def create_channel_manual(interaction: discord.Interaction, category_name: str, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=category_name)
    if category:
        new_ch = await category.create_text_channel(name=channel_name)
        await interaction.followup.send(f"✅ 생성 완료: {new_ch.mention}")
    else: await interaction.followup.send(f"⚠️ 카테고리 없음")

@bot.tree.command(name="채널삭제", description="수동 채널 삭제")
async def delete_channel_manual(interaction: discord.Interaction, category_name: str, channel_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=category_name)
    if category:
        target_channel = discord.utils.get(category.channels, name=channel_name)
        if target_channel:
            await target_channel.delete()
            await interaction.followup.send(f"🗑️ 삭제 완료")
        else: await interaction.followup.send(f"⚠️ 채널 없음")
    else: await interaction.followup.send(f"⚠️ 카테고리 없음")

@bot.tree.command(name="방생성", description="수동 방 생성")
async def manual_create_room_cmd(interaction: discord.Interaction, target: discord.Member):
    await interaction.response.defer(ephemeral=True)
    success, msg = await create_user_room(interaction.guild, target)
    if success: await interaction.followup.send(f"✅ **{msg}**")
    else: await interaction.followup.send(f"⚠️ **실패:** {msg}")

@bot.tree.command(name="방삭제", description="카테고리 삭제")
async def delete_room(interaction: discord.Interaction, target_name: str):
    await interaction.response.defer()
    category = discord.utils.get(interaction.guild.categories, name=target_name)
    if category:
        for ch in category.channels: await ch.delete()
        await category.delete()
        await interaction.followup.send("🗑️ 삭제 완료")
    else: await interaction.followup.send("❌ 못 찾음")

@bot.tree.command(name="재시작", description="재부팅")
async def restart_bot(interaction: discord.Interaction):
    if interaction.user.id in ALLOWED_USERS:
        await interaction.response.send_message("🔄 재부팅...", ephemeral=True)
        os.execl(sys.executable, sys.executable, *sys.argv)
    else: await interaction.response.send_message("❌ 권한 없음", ephemeral=True)

@bot.tree.command(name="자동역할설정", description="자동 역할")
async def set_auto_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)
    data[guild_id]["auto_role"] = role.id
    save_settings(data)
    await interaction.followup.send(f"✅ 완료: {role.mention}")

@bot.tree.command(name="도움역할설정", description="도움 역할")
async def set_help_role(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    data = migrate_data(data, guild_id)
    data[guild_id]["support_role"] = role.id
    save_settings(data)
    await interaction.followup.send(f"✅ 완료: {role.mention}")

@bot.tree.command(name="도움", description="관리자 호출")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    data = load_settings()
    guild_id = str(interaction.guild_id)
    if "support_role" in data[guild_id]:
        role = interaction.guild.get_role(data[guild_id]["support_role"])
        if role:
            await interaction.followup.send(f"📢 **도움 요청!**\n{role.mention}님, {interaction.user.mention}님이 호출함!")
            return
    await interaction.followup.send("⚠️ 역할 없음")

# -----------------------------------------------------------------
bot.run('')
# -----------------------------------------------------------------


