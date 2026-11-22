#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 700
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xatom.h>
#include "file_sorter_icon_x11.h"
#include <X11/keysym.h>
#include <X11/cursorfont.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <limits.h>
#include <time.h>
#include <ctype.h>
#include <math.h>

#define W 1130
#define H 714
#define MAX_DIRS 96
#define MAX_RULES 256
#define MAX_PATTERN 255
#define SHOW_ROWS 11
#define ROW_HEIGHT 29
#define LIST_Y 239
#define LIST_X 25
#define LIST_W 686
#define PANEL_X 735
#define PANEL_W 371

static const char *DEFAULT_RULES = "# File Sorter v3: scope, pattern, destination, mode (tab-separated)\nwatch\t*.7z\t~/Downloads/Archives\tarchive\nwatch\t*.zip\t~/Downloads/Archives\tarchive\nwatch\t*.tar.gz\t~/Downloads/Archives\tarchive\nwatch\t*.tar\t~/Downloads/Archives\tarchive\nwatch\t*.rar\t~/Downloads/Archives\tarchive\nwatch\t*.txt\t~/Sorted/Text Files/txt\tmove\nwatch\t*.ini\t~/Sorted/Text Files/ini\tmove\nwatch\t*.cfg\t~/Sorted/Configs\tmove\nwatch\t*.config\t~/Sorted/Configs\tmove\nwatch\t*.dll\t~/Sorted/DLLs\tmove\nwatch\t*.pdf\t~/Sorted/PDFs\tmove\nwatch\t*.bin\t~/Sorted/Binaries\tmove\nwatch\t*.BIN\t~/Sorted/Binaries\tmove\nwatch\t*.dat\t~/Sorted/Data Files\tmove\nwatch\t*.sh\t~/Sorted/Shell Scripts\tmove\nwatch\t*.log\t~/Sorted/Log Files\tmove\nwatch\t*.json\t~/Sorted/JSONs\tmove\nwatch\t*.js\t~/Sorted/Java Script Files\tmove\nwatch\t*.md\t~/Sorted/Markdown Files\tmove\nwatch\t*.bak\t~/Sorted/Backup Files\tmove\nwatch\t*.backup\t~/Sorted/Backup Files\tmove\nwatch\t*.lua\t~/Sorted/Lua Scripts\tmove\nwatch\t*.ps1\t~/Sorted/Power Shell Scripts\tmove\nwatch\t*.csv\t~/Sorted/CSVs\tmove\nwatch\t*.cs\t~/Sorted/C# Files\tmove\nwatch\t*.CS\t~/Sorted/C# Files\tmove\nwatch\t*.py\t~/Sorted/Python Scripts\tmove\nhome\t*.log\t~/Sorted/Log Files\tmove\nhome\t*.md\t~/Sorted/Markdown Files\tmove\nhome\t*.cs\t~/Sorted/C# Files\tmove\nhome\t*.CS\t~/Sorted/C# Files\tmove\nhome\t*.pdf\t~/Sorted/PDFs\tmove\nhome\t*.js\t~/Sorted/Java Scripts\tmove\nhome\t*.py\t~/Sorted/Python Scripts\tmove\nhome\t*.txt\t~/Sorted/Text Files/txt\tmove\nwatch\t*.AppImage\t~/Sorted/AppImages\tmove\n";

typedef struct {char scope[12]; char pattern[MAX_PATTERN+1]; char dest[PATH_MAX]; char mode[12]; int priority; char sources[PATH_MAX]; int recursive; int overwrite;} Rule;
static char dirs[MAX_DIRS][PATH_MAX];
static Rule rules[MAX_RULES];
static int dir_count=0, rule_count=0, selected_dir=-1,selected_rule=-1,doffset=0,roffset=0;
 static int tab=0,focus=0,scope_index=0,mode_index=0,confirm_reset=0,details_open=0,overwrite_enabled=0,confirm_overwrite=0,destination_per_folder=0;
static char interval_input[64]="2", source_input[PATH_MAX]="";
static int recursive_input=0,overwrite_input=0,confirm_overwrite_rule=-1;
static int details_page=0;static size_t caret_offset=0;
static char input1[MAX_PATTERN+1],input2[PATH_MAX],dir_file[PATH_MAX],rules_file[PATH_MAX],home[PATH_MAX],overwrite_file[PATH_MAX],scan_interval_file[PATH_MAX],destination_mode_file[PATH_MAX],status_msg[512];
static Display *dpy;static Window win;static GC gc;static XFontStruct *font,*bigfont;
static Atom wm_delete,clip_atom,utf8_atom;
static Atom xdnd_aware,xdnd_enter,xdnd_position,xdnd_status,xdnd_leave,xdnd_drop;
static Atom xdnd_finished,xdnd_selection,xdnd_typelist,xdnd_action_copy,uri_list,xdnd_data,incr_atom;
static Window drag_source=None,drag_reply_target=None;
static int drag_supported=0,drag_inside=0,drop_pending=0;
static unsigned long drag_version=0;static int screen,redraw=1;static volatile sig_atomic_t exiting=0;
static unsigned long bg,panel,header,ink,muted,green,orange,blue,red,line,active;
typedef struct {int x,y,w,h;} HotArea;
static HotArea hot_areas[128];static int hot_count=0,mouse_x=-1,mouse_y=-1;
static Cursor pointer_cursor,text_cursor;
static int row_hover=-1;
static int over_box(int x,int y,int w,int h){return mouse_x>=x&&mouse_x<x+w&&mouse_y>=y&&mouse_y<y+h;}
static int any_hot(int x,int y){for(int i=0;i<hot_count;i++){
    HotArea *a=&hot_areas[i];if(x>=a->x&&x<a->x+a->w&&y>=a->y&&y<a->y+a->h)return 1;
}return 0;}
static int pointer_mode=-1;
static void update_pointer(void){
    int mode=any_hot(mouse_x,mouse_y)?1:0;
    if((mouse_x>=200&&mouse_x<309&&mouse_y>=153&&mouse_y<182)||
       (tab==0&&mouse_x>=748&&mouse_x<1088&&mouse_y>=273&&mouse_y<316)||
       (tab==1&&mouse_x>=748&&mouse_x<1088&&mouse_y>=259&&mouse_y<300)||
       (tab==1&&details_open&&details_page==0&&mouse_x>=748&&mouse_x<990&&mouse_y>=399&&mouse_y<439)||
       (tab==1&&details_open&&details_page==1&&mouse_x>=748&&mouse_x<1088&&mouse_y>=503&&mouse_y<533))mode=2;
    if(mode!=pointer_mode){pointer_mode=mode;
        if(mode)XDefineCursor(dpy,win,mode==2?text_cursor:pointer_cursor);else XUndefineCursor(dpy,win);
    }
}
static pid_t picker=-1;static int picker_fd=-1,picker_target=0;
static char picker_result[PATH_MAX];static size_t picker_len=0;

static const char *scope_names[]={"WATCHED FOLDERS","HOME FOLDER ONLY","SORTED SAVES ONLY"};
static const char *scope_codes[]={"watch","home","saves"};
static const char *mode_names[]={"NORMAL MOVE","ARCHIVE (72-HOUR SPLIT)"};
static const char *mode_codes[]={"move","archive"};

static void on_signal(int sig){(void)sig;exiting=1;}
static void notice(const char *s){snprintf(status_msg,sizeof(status_msg),"%s",s);redraw=1;}
static unsigned long color(const char *s){XColor c,e;return XAllocNamedColor(dpy,DefaultColormap(dpy,screen),s,&c,&e)?c.pixel:WhitePixel(dpy,screen);}
static void rectangle(int x,int y,int w,int h,unsigned long c){XSetForeground(dpy,gc,c);XFillRectangle(dpy,win,gc,x,y,(unsigned)w,(unsigned)h);}
static void txt(int x,int y,const char *s,unsigned long c,int large){if(!s)return;XFontStruct *f=(large&&bigfont)?bigfont:font;if(f)XSetFont(dpy,gc,f->fid);XSetForeground(dpy,gc,c);XDrawString(dpy,win,gc,x,y,s,(int)strlen(s));}
static void fitted(int x,int y,const char *s,int width,unsigned long c){char cut[PATH_MAX+160];snprintf(cut,sizeof(cut),"%s",s?s:"");if(font){size_t n=strlen(cut);while(n>4&&XTextWidth(font,cut,(int)n)>width)cut[--n]=0;if(n<strlen(s)&&n>=4){cut[n-3]='.';cut[n-2]='.';cut[n-1]='.';}}txt(x,y,cut,c,0);}
static void button(int x,int y,int w,int h,const char *s,unsigned long c,int enabled){
    int hovered=enabled&&over_box(x,y,w,h);
    if(enabled&&hot_count<(int)(sizeof(hot_areas)/sizeof(hot_areas[0])))hot_areas[hot_count++]=(HotArea){x,y,w,h};
    rectangle(x,y,w,h,enabled?(hovered?active:c):header);
    if(hovered){XSetForeground(dpy,gc,green);XDrawRectangle(dpy,win,gc,x,y,w-1,h-1);}
    int tw=font?XTextWidth(font,s,(int)strlen(s)):(int)strlen(s)*9;
    txt(x+(w-tw)/2,y+h/2+5,s,enabled?ink:muted,0);
}
static char *edit_buffer(int which,size_t *cap){
    if(which==1){*cap=sizeof(input1);return input1;}
    if(which==2){*cap=sizeof(input2);return input2;}
    if(which==3){*cap=sizeof(interval_input);return interval_input;}
    if(which==5){*cap=sizeof(source_input);return source_input;}
    *cap=0;return NULL;
}
static void set_focus(int which){focus=which;size_t cap=0;char *s=edit_buffer(which,&cap);caret_offset=s?strlen(s):0;redraw=1;}
static void edit_field(int x,int baseline,int width,const char *value,int focused){
    if(!value)value="";
    size_t len=strlen(value),pos=caret_offset;
    if(pos>len)pos=len;
    size_t start=0,end=len;
    int maxwidth=width-14;
    if(font){
        while(start<pos && XTextWidth(font,value+start,(int)(pos-start))>maxwidth-10)start++;
        end=start;
        while(end<len && XTextWidth(font,value+start,(int)(end-start+1))<maxwidth)end++;
    }
    char visible[PATH_MAX+64];size_t count=end-start;
    if(count>=sizeof(visible))count=sizeof(visible)-1;
    memcpy(visible,value+start,count);visible[count]=0;
    txt(x+7,baseline,visible,ink,0);
    if(focused){
        struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
        if(((t.tv_sec*1000L+t.tv_nsec/1000000L)/550)%2==0){
            int offset=(font&&pos>=start)?XTextWidth(font,value+start,(int)(pos-start)):0;
            if(offset>maxwidth)offset=maxwidth;
            XSetForeground(dpy,gc,green);XDrawLine(dpy,win,gc,x+7+offset,baseline-16,x+7+offset,baseline+5);
        }
    }
}
static int in_rect(int px,int py,int x,int y,int w,int h){return px>=x&&px<x+w&&py>=y&&py<y+h;}
static int mkpath(const char *dir){char p[PATH_MAX];if(strlen(dir)>=PATH_MAX)return -1;strcpy(p,dir);for(char *k=p+1;*k;k++){if(*k=='/'){*k=0;if(mkdir(p,0700)!=0&&errno!=EEXIST)return -1;*k='/';}}if(mkdir(p,0700)!=0&&errno!=EEXIST)return -1;return 0;}
static int atomic_open(char *temp,size_t n,const char *path){char parent[PATH_MAX];if(strlen(path)>=PATH_MAX-16)return -1;snprintf(parent,sizeof(parent),"%s",path);char *cut=strrchr(parent,'/');if(!cut)return -1;*cut=0;if(mkpath(parent)<0)return -1;snprintf(temp,n,"%s.tmpXXXXXX",path);return mkstemp(temp);}
static int flush_atomic(FILE *f,int fd,const char *tmp,const char *dest){int ok=fflush(f)==0;ok=fsync(fd)==0&&ok;ok=fclose(f)==0&&ok;if(ok&&rename(tmp,dest)==0)return 0;unlink(tmp);return -1;}
/* Persist folders beneath this user's HOME using ~/, not a particular login name.
 * The Bash worker expands ~ explicitly when reading monitored directories. */
static int portable_home_path(const char *absolute,char *out,size_t cap){
    size_t hlen=strlen(home);
    while(hlen>1 && home[hlen-1]=='/')hlen--;
    const char *value=absolute;
    char converted[PATH_MAX];
    if(hlen && strncmp(absolute,home,hlen)==0 &&
       (absolute[hlen]=='/' || absolute[hlen]=='\0')){
        if(snprintf(converted,sizeof(converted),"~%s",absolute+hlen)>=(int)sizeof(converted))return 0;
        value=converted;
    }
    return snprintf(out,cap,"%s",value)<(int)cap;
}
static int save_directories(void){char tmp[PATH_MAX];int fd=atomic_open(tmp,sizeof(tmp),dir_file);if(fd<0)return -1;FILE *f=fdopen(fd,"w");if(!f){close(fd);unlink(tmp);return -1;}for(int i=0;i<dir_count;i++)if(fprintf(f,"%s\n",dirs[i])<0){fclose(f);unlink(tmp);return -1;}return flush_atomic(f,fd,tmp,dir_file);}
static void load_overwrite(void){
    char setting[32]={0};overwrite_enabled=0;
    FILE *f=fopen(overwrite_file,"r");
    if(f){if(fgets(setting,sizeof(setting),f) && !strcmp(setting,"on\n"))overwrite_enabled=1;fclose(f);}
    confirm_overwrite=0;
}
static int save_rules(void);
/* The top button is a bulk shortcut; an individual rule is authoritative. */
static void toggle_overwrite(void){
    if(!rule_count){notice("Add a sorting rule before enabling overwriting.");return;}
    int on=0;for(int i=0;i<rule_count;i++)on+=rules[i].overwrite;
    int enable=(on!=rule_count);
    if(enable && !confirm_overwrite){
        confirm_overwrite=1;
        notice("WARNING: bulk enabling may replace files. Click CONFIRM OVERWRITE ALL again.");return;
    }
    int previous[MAX_RULES];for(int i=0;i<rule_count;i++){previous[i]=rules[i].overwrite;rules[i].overwrite=enable;}
    if(save_rules()!=0){for(int i=0;i<rule_count;i++)rules[i].overwrite=previous[i];notice("ERROR saving overwrite settings.");return;}
    if(selected_rule>=0&&selected_rule<rule_count)overwrite_input=rules[selected_rule].overwrite;
    confirm_overwrite=0;confirm_overwrite_rule=-1;
    notice(enable?"Overwrite enabled for ALL existing rules. Individual toggles can override.":
                  "Overwrite disabled for all rules. Custom rules can still be toggled separately.");
    redraw=1;
}
static void load_destination_mode(void){
    destination_per_folder=0;
    char setting[40]={0};FILE *f=fopen(destination_mode_file,"r");
    if(f){if(fgets(setting,sizeof(setting),f) && !strcmp(setting,"per-folder\n"))destination_per_folder=1;fclose(f);}
}
static void toggle_destination_mode(void){
    char tmp[PATH_MAX];int fd=atomic_open(tmp,sizeof(tmp),destination_mode_file);
    if(fd<0){notice("Could not save destination mode.");return;}
    FILE *f=fdopen(fd,"w");if(!f){close(fd);unlink(tmp);notice("Could not save destination mode.");return;}
    fputs(destination_per_folder?"shared\n":"per-folder\n",f);
    if(flush_atomic(f,fd,tmp,destination_mode_file)!=0){notice("Could not save destination mode.");return;}
    destination_per_folder=!destination_per_folder;
    notice(destination_per_folder?"Per-folder mode: each watched directory uses its own Sorted/." :
                                  "Shared mode: destinations below ~/Sorted/ stay centralized.");
}
static int parse_interval(const char *raw,double *number){
    if(!raw||!*raw||strlen(raw)>48)return 0;
    for(const char *p=raw;*p;p++)if(!isdigit((unsigned char)*p)&&*p!='.')return 0;
    char *end=NULL;errno=0;double value=strtod(raw,&end);
    if(errno==ERANGE||!end||*end||!isfinite(value)||value<=0.0)return 0;
    *number=value;return 1;
}
static void load_interval(void){
    strcpy(interval_input,"2");FILE *f=fopen(scan_interval_file,"r");
    if(!f)return;
    char linebuf[80]={0};if(fgets(linebuf,sizeof(linebuf),f)){
        linebuf[strcspn(linebuf,"\r\n")]=0;
        double val;
        if(parse_interval(linebuf,&val))snprintf(interval_input,sizeof(interval_input),"%s",linebuf);
    }
    fclose(f);
}
static void save_interval(void){
    double value=0;
    if(!parse_interval(interval_input,&value)){
        notice("Invalid interval. Enter a positive number of seconds (e.g., 0.1 or 2.5).");return;
    }
    char tmp[PATH_MAX];int fd=atomic_open(tmp,sizeof(tmp),scan_interval_file);
    if(fd<0){notice("Could not save check interval.");return;}
    FILE *f=fdopen(fd,"w");if(!f){close(fd);unlink(tmp);notice("Could not save check interval.");return;}
    fprintf(f,"%s\n",interval_input);
    if(flush_atomic(f,fd,tmp,scan_interval_file)!=0){notice("Could not save check interval.");return;}
    focus=0;
    notice("Check interval saved. Changes apply after the current scan.");
}
static void step_interval(int direction){
    double value;
    if(!parse_interval(interval_input,&value))value=2.0;
    double next=value+(direction*0.1);
    if(next<=0.0)next=0.1;
    if(!isfinite(next)){notice("Interval is too large to increment.");return;}
    snprintf(interval_input,sizeof(interval_input),"%.12g",next);
    save_interval();
}
static int save_rules(void){char tmp[PATH_MAX];int fd=atomic_open(tmp,sizeof(tmp),rules_file);if(fd<0)return -1;FILE *f=fdopen(fd,"w");if(!f){close(fd);unlink(tmp);return -1;}fputs("# rule-order: position; first listed rule wins (1/N is highest)\n# scope<TAB>pattern<TAB>destination<TAB>mode<TAB>position-rank<TAB>source-folders<TAB>recursive(0/1)<TAB>overwrite(0/1)\n",f);for(int i=0;i<rule_count;i++){rules[i].priority=rule_count-i;if(fprintf(f,"%s\t%s\t%s\t%s\t%d\t%s\t%d\t%d\n",rules[i].scope,rules[i].pattern,rules[i].dest,rules[i].mode,rules[i].priority,rules[i].sources,rules[i].recursive,rules[i].overwrite)<0){fclose(f);unlink(tmp);return -1;}}return flush_atomic(f,fd,tmp,rules_file);}
static int index_of(const char *s,const char *const *options,int count){for(int i=0;i<count;i++)if(!strcmp(s,options[i]))return i;return -1;}
static int is_valid_rule(const Rule *r){
    if(index_of(r->scope,scope_codes,3)<0||index_of(r->mode,mode_codes,2)<0)return 0;
    if(!*r->pattern||strlen(r->pattern)>MAX_PATTERN||strchr(r->pattern,'/')||strchr(r->pattern,'\n')||strchr(r->pattern,'\r')||strchr(r->pattern,'\t'))return 0;
    const char *p=r->dest;
    if(!(*p=='/'||(p[0]=='~'&&(p[1]=='/'||!p[1]))))return 0;
    if(strchr(p,'\r')||strchr(p,'\n')||strchr(p,'\t')||strstr(p,"/../")||strstr(p,"/./")||strstr(p,"//")||p[strlen(p)-1]=='/' )return 0;
    if(!strcmp(p,"/")||!strcmp(p,"~")||!strcmp(p,home))return 0;
    if(!strcmp(r->mode,"archive")){
        if(strncmp(r->pattern,"*.",2)||!r->pattern[2])return 0;
        for(const char *q=r->pattern+2;*q;q++)if(!(isalnum((unsigned char)*q)||*q=='.'||*q=='_'||*q=='-'))return 0;
    }
    if(r->priority<0||r->priority>9999||r->recursive<0||r->recursive>1||r->overwrite<0||r->overwrite>1)return 0;
    if(strcmp(r->sources,"-")){
        if(strcmp(r->scope,"watch")||!*r->sources||strchr(r->sources,'\t')||strchr(r->sources,'\n')||strchr(r->sources,'\r'))return 0;
        char tmp[PATH_MAX];snprintf(tmp,sizeof(tmp),"%s",r->sources);
        char *p=tmp,*part;int parts=0;
        while((part=strsep(&p,"|"))!=NULL){
            if(!*part||++parts>32)return 0;
            if(!(part[0]=='/'||(part[0]=='~'&&part[1]=='/')))return 0;
            if(strstr(part,"/../")||strstr(part,"/./")||strstr(part,"//"))return 0;
        }
    }
    return 1;
}
static int parse_rule(char *s,Rule *r){
    if(*s=='#'||!*s)return 0;
    memset(r,0,sizeof(*r));r->priority=0;r->recursive=0;r->overwrite=overwrite_enabled;strcpy(r->sources,"-");
    char *part[8]={0},*p=s;int n=0;
    while(p&&n<8)part[n++]=strsep(&p,"\t");
    if(p||!(n==4||n==6||n==7||n==8))return 0;
    if(strlen(part[0])>=sizeof(r->scope)||strlen(part[1])>=sizeof(r->pattern)||strlen(part[2])>=sizeof(r->dest)||strlen(part[3])>=sizeof(r->mode))return 0;
    strcpy(r->scope,part[0]);strcpy(r->pattern,part[1]);strcpy(r->dest,part[2]);strcpy(r->mode,part[3]);
    if(n>=6){
        if(!part[4]||strspn(part[4],"0123456789")!=strlen(part[4])||strlen(part[4])>4||strlen(part[5])>=sizeof(r->sources))return 0;
        r->priority=atoi(part[4]);strcpy(r->sources,part[5]);
    }
    if(n>=7){if(!part[6]|| (strcmp(part[6],"0") && strcmp(part[6],"1")))return 0;r->recursive=atoi(part[6]);}
    if(n==8){if(!part[7]|| (strcmp(part[7],"0") && strcmp(part[7],"1")))return 0;r->overwrite=atoi(part[7]);}
    return is_valid_rule(r);
}

static void load_directories(void){
    FILE *f=fopen(dir_file,"r");dir_count=0;selected_dir=-1;doffset=0;
    if(!f){
        if(save_directories()!=0)notice("Could not initialize empty watched folders.");
        else notice("New setup: choose which folders to monitor. Downloads and Documents are suggested.");
        return;
    }
    char *line=NULL;size_t cap=0;ssize_t n;int migrated=0;
    while(dir_count<MAX_DIRS&&(n=getline(&line,&cap,f))>=0){
        while(n>0&&(line[n-1]=='\r'||line[n-1]=='\n'))line[--n]=0;
        if(n==0||n>=PATH_MAX||strchr(line,'\t'))continue;
        if(line[0]!='/' && !(line[0]=='~'&&(line[1]=='/'||line[1]=='\0')))continue;
        char portable[PATH_MAX];
        if(!portable_home_path(line,portable,sizeof(portable)))continue;
        if(strcmp(line,portable)!=0)migrated=1;
        strcpy(dirs[dir_count++],portable);
    }
    free(line);fclose(f);
    /* This only rewrites paths actually beneath this user's home; any external
       absolute paths, including other mounted drives, remain unchanged. */
    if(migrated && save_directories()!=0)notice("Could not migrate monitored folders to ~/ paths.");
}
static void load_rules(void){
    FILE *f=fopen(rules_file,"r");rule_count=0;selected_rule=-1;roffset=0;int positional=0;
    if(!f){char *buf=strdup(DEFAULT_RULES);if(!buf){notice("Out of memory");return;}char *save=NULL;for(char *line=strtok_r(buf,"\n",&save);line&&rule_count<MAX_RULES;line=strtok_r(NULL,"\n",&save)){
        Rule r;if(parse_rule(line,&r)){r.overwrite=0;rules[rule_count++]=r;}
    }free(buf);if(save_rules()<0)notice("Could not create default rules file");return;}
    char *line=NULL;size_t cap=0;ssize_t n;
    while(rule_count<MAX_RULES&&(n=getline(&line,&cap,f))>=0){while(n>0&&(line[n-1]=='\r'||line[n-1]=='\n'))line[--n]=0;if(!strcmp(line,"# rule-order: position; first listed rule wins (1/N is highest)"))positional=1;Rule r;if(parse_rule(line,&r))rules[rule_count++]=r;}
    free(line);fclose(f);
    /* Preserve v1.3.8 effective numeric priority once on first opening. */
    if(!positional)for(int i=1;i<rule_count;i++){Rule key=rules[i];int j=i-1;while(j>=0&&rules[j].priority<key.priority){rules[j+1]=rules[j];j--;}rules[j+1]=key;}
    for(int i=0;i<rule_count;i++)rules[i].priority=rule_count-i;
}
static void clear_rule_edit(void){selected_rule=-1;input1[0]=0;input2[0]=0;scope_index=0;mode_index=0;source_input[0]=0;recursive_input=0;overwrite_input=0;confirm_overwrite_rule=-1;focus=1;caret_offset=0;details_open=1;details_page=0;notice("New file format: enter an extension, choose a destination, then SAVE RULE.");redraw=1;}
static void choose_rule(int n){if(n<0||n>=rule_count)return;selected_rule=n;Rule *r=&rules[n];strcpy(input1,r->pattern);portable_home_path(r->dest,input2,sizeof(input2));scope_index=index_of(r->scope,scope_codes,3);mode_index=index_of(r->mode,mode_codes,2);snprintf(source_input,sizeof(source_input),"%s",!strcmp(r->sources,"-")?"":r->sources);recursive_input=r->recursive;overwrite_input=r->overwrite;focus=0;redraw=1;}
static void choose_directory(int n){if(n<0||n>=dir_count)return;selected_dir=n;snprintf(input2,sizeof(input2),"%s",dirs[n]);focus=0;redraw=1;}
static void reload_files(void){load_directories();load_overwrite();load_rules();input1[0]=input2[0]=0;load_interval();load_destination_mode();notice("Reloaded rules, watched folders, check interval, and overwrite setting from disk.");}
static void normalize_dir(const char *raw,char *out){out[0]=0;char *expanded=NULL;
    if(raw[0]=='~'&&(raw[1]=='/'||!raw[1])){if(asprintf(&expanded,"%s%s",home,raw+1)<0)return;}
    else if(raw[0]=='/'){expanded=strdup(raw);}else{if(asprintf(&expanded,"%s/%s",home,raw)<0)return;}
    if(expanded){char *r=realpath(expanded,NULL);if(r){if(strlen(r)<PATH_MAX)strcpy(out,r);free(r);}free(expanded);}
}
static int path_within(const char *p,const char *parent){size_t n=strlen(parent);return !strncmp(p,parent,n)&&(p[n]=='/'||!p[n]);}
static void add_directory(void){char p[PATH_MAX];if(!*input2){notice("Enter a folder path first.");return;}normalize_dir(input2,p);if(!*p){notice("That folder does not exist.");return;}
    struct stat st;if(stat(p,&st)!=0||!S_ISDIR(st.st_mode)){notice("Select a real directory.");return;}
    char sortroot[PATH_MAX],archive[PATH_MAX];snprintf(sortroot,sizeof(sortroot),"%s/Sorted",home);snprintf(archive,sizeof(archive),"%s/Downloads/Archives",home);
    if(!strcmp(p,"/")||!strcmp(p,"/home")||!strcmp(p,"/run")||path_within(p,sortroot)||path_within(p,archive)){notice("Cannot watch filesystem roots or default output folders.");return;}
    for(int i=0;i<dir_count;i++){
        char existing[PATH_MAX];normalize_dir(dirs[i],existing);
        if(!strcmp(existing,p)){selected_dir=i;notice("This directory is already monitored.");return;}
    }
    if(dir_count>=MAX_DIRS){notice("Maximum of 96 watched directories reached.");return;}
    if(!portable_home_path(p,dirs[dir_count],sizeof(dirs[dir_count]))){notice("Folder path too long.");return;}
    dir_count++;selected_dir=dir_count-1;if(selected_dir>=doffset+SHOW_ROWS)doffset=selected_dir-SHOW_ROWS+1;
    if(save_directories()==0)notice("Watched directory added; sorter will pick it up on its next scan.");else notice("ERROR saving watched directories.");input2[0]=0;focus=0;redraw=1;
}
static void add_suggestion(const char *name){
    if(snprintf(input2,sizeof(input2),"~/%s",name)>=(int)sizeof(input2)){notice("Folder name too long.");return;}
    add_directory();
}
static void remove_directory(void){if(selected_dir<0||selected_dir>=dir_count){notice("Choose a directory before removing it.");return;}
    if(selected_dir<dir_count-1)memmove(&dirs[selected_dir],&dirs[selected_dir+1],(size_t)(dir_count-selected_dir-1)*sizeof(dirs[0]));dir_count--;selected_dir=-1;
    if(doffset>dir_count-SHOW_ROWS)doffset=dir_count>SHOW_ROWS?dir_count-SHOW_ROWS:0;
    if(save_directories()==0)notice("Directory removed from monitoring (files untouched).");else notice("ERROR saving watched directories.");input2[0]=0;redraw=1;
}
static void save_rule_edit(void){Rule r={0};char pattern[MAX_PATTERN+1];snprintf(pattern,sizeof(pattern),"%s",input1);
    /* Allow .cbz, cbz and *.cbz; preserve advanced glob patterns like *Trainer.exe. */
    size_t n=strlen(pattern);
    while(n && isspace((unsigned char)pattern[n-1]))pattern[--n]=0;
    char *start=pattern;while(isspace((unsigned char)*start))start++;
    if(start!=pattern)memmove(pattern,start,strlen(start)+1);
    n=strlen(pattern);
    int simple_extension=(n>0);
    for(size_t i=0;i<n;i++)if(!(isalnum((unsigned char)pattern[i])||pattern[i]=='_'||pattern[i]=='-'||pattern[i]=='.'))simple_extension=0;
    if(simple_extension && (pattern[0]=='.' || strchr(pattern,'.')==NULL)){
        const char *ext=pattern[0]=='.'?pattern+1:pattern;
        char expanded[MAX_PATTERN+1];
        int count=snprintf(expanded,sizeof(expanded),"*.%s",ext);
        if(count<0||count>MAX_PATTERN){notice("Extension is too long.");return;}
        strcpy(pattern,expanded);
    }
    if(!*input2){details_open=1;focus=2;notice("Choose a destination folder under DESTINATION & OPTIONS first.");return;}
    strcpy(r.scope,scope_codes[scope_index]);strcpy(r.mode,mode_codes[mode_index]);strcpy(r.pattern,pattern);
    /* Destination paths can be anywhere writable. Bare relative paths mean ~/... .
     * Keep output as an absolute path or ~/-prefixed path for the existing v3.1 sorter. */
    char destination[PATH_MAX];
    const char *begin=input2;
    while(isspace((unsigned char)*begin))begin++;
    if(begin[0]=='/' || (begin[0]=='~' && begin[1]=='/')){
        if(snprintf(destination,sizeof(destination),"%s",begin)>=(int)sizeof(destination)){
            notice("Destination path too long.");return;
        }
    }else if(begin[0] && begin[0]!='~'){
        if(snprintf(destination,sizeof(destination),"~/%s",begin)>=(int)sizeof(destination)){
            notice("Destination path too long.");return;
        }
    }else{
        notice("Choose a folder path, such as ~/Music or /mnt/storage/Music.");return;
    }
    size_t dlen=strlen(destination);
    while(dlen>0 && isspace((unsigned char)destination[dlen-1]))destination[--dlen]=0;
    while(dlen>1 && destination[dlen-1]=='/')destination[--dlen]=0;
    if(!strcmp(destination,"~") || !strcmp(destination,"/")){
        notice("Choose a subfolder rather than the filesystem/home root.");return;
    }
    if(!portable_home_path(destination,r.dest,sizeof(r.dest))){notice("Destination path too long.");return;}
    r.priority=0; r.recursive=recursive_input; r.overwrite=overwrite_input; /* Actual rank assigned from the list. */
    snprintf(r.sources,sizeof(r.sources),"%s",*source_input?source_input:"-");
    if(!is_valid_rule(&r)){details_open=1;notice("Invalid rule: use .zip and a writable folder (~/Music or /mnt/storage).");return;}
    if(selected_rule>=0&&selected_rule<rule_count){rules[selected_rule]=r;}else{
        if(rule_count>=MAX_RULES){notice("Maximum 256 rules reached.");return;}
        rules[rule_count]=r;selected_rule=rule_count++;roffset=selected_rule>=SHOW_ROWS?selected_rule-SHOW_ROWS+1:0;
    }
    if(save_rules()==0){snprintf(input2,sizeof(input2),"%s",r.dest);notice("Rule saved. First matching rule in list wins on next scan.");}
    else notice("ERROR saving rules file.");redraw=1;
}
static void remove_rule(void){if(selected_rule<0||selected_rule>=rule_count){notice("Select a rule first.");return;}
    if(selected_rule<rule_count-1)memmove(&rules[selected_rule],&rules[selected_rule+1],(size_t)(rule_count-selected_rule-1)*sizeof(rules[0]));rule_count--;selected_rule=-1;input1[0]=input2[0]=0;
    if(roffset>rule_count-SHOW_ROWS)roffset=rule_count>SHOW_ROWS?rule_count-SHOW_ROWS:0;
    if(save_rules()==0)notice("Rule removed; files already sorted remain untouched.");else notice("ERROR saving rules file.");redraw=1;
}
static void shift_rule(int direction){int i=selected_rule;int j=i+direction;if(i<0||j<0||j>=rule_count){notice("Select a rule that can move in that direction.");return;}Rule r=rules[i];rules[i]=rules[j];rules[j]=r;selected_rule=j;
    if(selected_rule<roffset)roffset=selected_rule;if(selected_rule>=roffset+SHOW_ROWS)roffset=selected_rule-SHOW_ROWS+1;
    if(save_rules()==0)notice("Rule moved. First matching rule in list wins.");else notice("ERROR saving reordered rules.");redraw=1;
}
static void reset_rules(void){
    if(!confirm_reset){confirm_reset=1;notice("Click RESTORE DEFAULTS again to replace all custom sorting rules.");return;}
    confirm_reset=0;
    char *buf=strdup(DEFAULT_RULES);
    if(!buf){notice("Out of memory; no rules changed.");return;}
    Rule restored[MAX_RULES];int count=0;
    char *state=NULL;
    for(char *entry=strtok_r(buf,"\n",&state);entry&&count<MAX_RULES;entry=strtok_r(NULL,"\n",&state)){
        Rule r;if(parse_rule(entry,&r)){r.overwrite=0;restored[count++]=r;}
    }
    free(buf);
    memcpy(rules,restored,(size_t)count*sizeof(Rule));rule_count=count;
    selected_rule=-1;roffset=0;input1[0]=input2[0]=0;
    if(save_rules()==0)notice("Default rules restored. Watched folders were kept.");
    else notice("ERROR saving default rules file.");
    redraw=1;
}

#include "menu_bridge.h"
#define UPDATE_NOTIFY(message) notice(message)
#include "sorter_update.h"
static void draw_header(void){rectangle(0,0,W,H,bg);rectangle(0,0,W,5,green);txt(25,43,"FILE SORTER",ink,1);txt(27,66,"Configuration Editor v1.3.12  |  SteamOS / Linux",muted,0);
    button(915,22,190,42,"BACK TO MENU",blue,1);
    button(25,96,234,42,"WATCHED FOLDERS",tab==0?blue:header,1);button(269,96,234,42,"SORTING RULES",tab==1?blue:header,1);
    button(530,96,170,42,su_auto_enabled?"AUTO UPDATE: ON":"AUTO UPDATE: OFF",blue,1);
    button(713,96,200,42,"UPDATE NOW",green,1);
    button(930,96,175,42,"RELOAD FROM DISK",blue,1);
    rectangle(25,151,1080,33,panel);
    txt(35,172,"CHECK INTERVAL (s)",muted,0);
    rectangle(200,153,109,29,focus==3?active:header);
    edit_field(201,173,105,interval_input,focus==3);
    button(317,153,46,14,"^",blue,1);
    button(317,168,46,14,"v",blue,1);
    button(374,153,80,29,"APPLY",green,1);
    txt(470,173,"Up/Down: 0.1",muted,0);
    int on=0;for(int i=0;i<rule_count;i++)on+=rules[i].overwrite;
    const char *bulk=confirm_overwrite?"CONFIRM OVERWRITE ALL":(on==0?"OVERWRITE ALL: OFF":(on==rule_count?"OVERWRITE ALL: ON":"OVERWRITE: MIXED"));
    button(825,152,279,31,bulk,on?red:blue,1);
}
static void draw_dirs(void){
    rectangle(25,199,686,427,panel);txt(40,227,"MONITORED DIRECTORIES",ink,1);
    for(int row=0;row<SHOW_ROWS;row++){int i=doffset+row;if(i>=dir_count)break;int y=LIST_Y+ROW_HEIGHT*row;
        if(i==selected_dir||i==row_hover)rectangle(30,y,674,27,i==selected_dir?active:header);if(row>0)rectangle(39,y,655,1,line);
        char label[PATH_MAX+16];snprintf(label,sizeof(label),"%02d   %s",i+1,dirs[i]);fitted(45,y+19,label,645,i==selected_dir?ink:muted);
    }
    button(37,583,159,35,"PREVIOUS",blue,doffset>0);button(204,583,159,35,"NEXT",blue,doffset+SHOW_ROWS<dir_count);
    char count[80];snprintf(count,sizeof(count),"%d monitored directories",dir_count);txt(389,606,count,muted,0);
    rectangle(PANEL_X,199,PANEL_W,427,panel);txt(750,229,"ADD / REMOVE FOLDERS",ink,1);
    txt(750,261,"Folder path",muted,0);rectangle(748,273,340,43,focus==2?active:header);
    if(*input2)edit_field(750,301,336,input2,focus==2);else {txt(758,301,"~/Downloads or /mnt/storage/Mods",muted,0);if(focus==2)edit_field(750,301,336,"",1);}
    button(748,340,340,44,"BROWSE FOR DIRECTORY",blue,1);
    button(748,404,340,46,"ADD DIRECTORY",green,1);
    button(748,464,340,46,"REMOVE SELECTED",red,selected_dir>=0);
    button(748,512,166,25,"ADD DOWNLOADS",blue,1);
    button(922,512,166,25,"ADD DOCUMENTS",blue,1);
    button(748,547,340,34,destination_per_folder?"DESTINATION: EACH FOLDER /Sorted":"DESTINATION: SHARED ~/Sorted",blue,1);
    txt(750,598,"Switch affects only ~/Sorted/ destinations.",muted,0);
    txt(750,615,"Custom output paths stay unchanged.",muted,0);
}
static void draw_rules(void){
    rectangle(25,199,686,427,panel);txt(41,225,"SORTING RULES",ink,1);
    txt(43,246,"R",muted,0);txt(75,246,"O",muted,0);txt(106,246,"Rank",muted,0);txt(165,246,"Scope",muted,0);txt(234,246,"Pattern",muted,0);txt(360,246,"Destination",muted,0);txt(629,246,"Mode",muted,0);
    for(int row=0;row<SHOW_ROWS;row++){int i=roffset+row;if(i>=rule_count)break;int y=253+ROW_HEIGHT*row;
        if(i==selected_rule||i==row_hover)rectangle(30,y,675,27,i==selected_rule?active:header);if(row>0)rectangle(40,y,654,1,line);
        char scope[30],num[24];snprintf(num,sizeof(num),"%d/%d",i+1,rule_count);snprintf(scope,sizeof(scope),"%s",rules[i].scope);
        button(37,y+3,26,22,rules[i].recursive?"[x]":"[ ]",rules[i].recursive?green:blue,1);
        button(69,y+3,26,22,confirm_overwrite_rule==i?"[!]":(rules[i].overwrite?"[x]":"[ ]"),rules[i].overwrite?red:blue,1);
        txt(107,y+19,num,i==selected_rule?ink:muted,0);fitted(164,y+19,scope,64,muted);
        fitted(234,y+19,rules[i].pattern,117,ink);fitted(361,y+19,rules[i].dest,251,ink);
        txt(629,y+19,!strcmp(rules[i].mode,"archive")?"72h":"Move",!strcmp(rules[i].mode,"archive")?green:muted,0);
    }
    button(32,582,120,35,"PREVIOUS",blue,roffset>0);
    button(159,582,120,35,"NEXT",blue,roffset+SHOW_ROWS<rule_count);
    button(287,582,120,35,"MOVE UP",blue,selected_rule>0);
    button(415,582,120,35,"MOVE DOWN",blue,selected_rule>=0&&selected_rule<rule_count-1);
    char label[60];snprintf(label,sizeof(label),"%d rules",rule_count);txt(553,605,label,muted,0);

    rectangle(PANEL_X,199,PANEL_W,427,panel);
    txt(749,225,selected_rule>=0?"EDIT FILE FORMAT":"ADD A FILE FORMAT",ink,1);
    txt(749,249,"File extension / pattern",muted,0);
    rectangle(748,259,340,41,focus==1?active:header);
    if(*input1)edit_field(750,286,336,input1,focus==1);else {txt(758,286,"e.g., .cbz or *.tar.gz",muted,0);if(focus==1)edit_field(750,286,336,"",1);}
    rectangle(748,306,340,24,drag_inside?green:header);
    txt(756,323,drag_inside?"RELEASE TO DETECT FORMAT":"DRAG A FILE HERE TO DETECT FORMAT",drag_inside?ink:muted,0);
    button(748,333,340,36,details_open?"v  DESTINATION & OPTIONS  (HIDE)":">  DESTINATION & OPTIONS  (SHOW)",blue,1);
    if(details_open){
        button(748,376,165,25,"DESTINATION / MODE",details_page==0?active:blue,1);
        button(920,376,168,25,"PRIORITY / SOURCES",details_page==1?active:blue,1);
        if(details_page==0){
            rectangle(748,410,242,38,focus==2?active:header);
            if(*input2)edit_field(750,436,238,input2,focus==2);
            else {txt(757,436,"~/Music or /run/media/...",muted,0);if(focus==2)edit_field(750,436,238,"",1);}
            button(996,410,92,38,"BROWSE",blue,1);
            txt(749,466,"Apply to",muted,0);
            button(748,473,340,36,scope_names[scope_index],blue,1);
            txt(749,523,"Sorting behavior",muted,0);
            button(748,529,340,35,mode_names[mode_index],blue,1);
        }else{
            txt(750,414,"Priority = list position (first wins)",muted,0);
            char rank[100];if(selected_rule>=0)snprintf(rank,sizeof(rank),"%d/%d  - use MOVE UP / DOWN",selected_rule+1,rule_count);else snprintf(rank,sizeof(rank),"New rule: %d/%d (last)",rule_count+1,rule_count+1);
            rectangle(748,418,340,34,header);txt(759,441,rank,ink,0);
            button(748,454,340,25,recursive_input?"[x] SEARCH SUBFOLDERS: ON":"[ ] SEARCH SUBFOLDERS: OFF",recursive_input?green:blue,1);
            button(748,482,340,25,overwrite_input?"[x] OVERWRITE FOR THIS RULE: ON":"[ ] OVERWRITE FOR THIS RULE: OFF",overwrite_input?red:blue,1);
            txt(750,522,"Rule-specific watch folders (| separated)",muted,0);
            rectangle(748,526,340,26,focus==5?active:header);
            if(*source_input)edit_field(750,545,336,source_input,focus==5);
            else{txt(757,545,"All Watched Folders (default)",muted,0);if(focus==5)edit_field(750,545,336,"",1);}
            button(748,554,164,24,"ADD FOLDER",blue,1);
            button(920,554,168,24,"USE ALL WATCHED",blue,1);
        }
    }else{
        txt(749,397,"Destination (any writable folder):",muted,0);
        if(*input2)fitted(749,422,input2,336,ink);else txt(749,422,"No destination selected",orange,0);
        txt(749,459,"Applies to:",muted,0);
        fitted(749,481,scope_names[scope_index],334,ink);
        txt(749,516,!mode_index?"Normal move":"72-hour New / Old archive sorting",muted,0);
        txt(749,548,"Expand for rank and watched folders. Move Up/Down to reorder.",muted,0);
    }
    button(748,583,111,37,"NEW FORMAT",blue,1);
    button(866,583,106,37,"SAVE RULE",green,1);
    button(980,583,108,37,"DELETE",red,selected_rule>=0);
}
static void render(void){hot_count=0;draw_header();if(tab==0)draw_dirs();else draw_rules();
    rectangle(25,643,1080,55,panel);
    fitted(39,663,status_msg,865,ink);
    if(tab==0){txt(39,685,"Tip: Ctrl+1/2 tabs, Ctrl+M menu, Up/Down select a folder.",muted,0);
    }else{txt(39,685,"Tip: Ctrl+1/2 tabs, Ctrl+R reload, Up/Down select a rule.",muted,0);
        button(926,662,171,28,confirm_reset?"CONFIRM RESET":"RESTORE DEFAULTS",red,1);
    }
    update_pointer();XFlush(dpy);redraw=0;
}

static void picker_open(int target){
    if(picker>0){notice("Folder picker already open.");return;}
    /* Start browsing where the current destination lives, not always $HOME. */
    char initial[PATH_MAX];snprintf(initial,sizeof(initial),"%s",home);
    if(*input2){
        char expanded[PATH_MAX];
        if(input2[0]=='~' && input2[1]=='/'){
            if(snprintf(expanded,sizeof(expanded),"%s/%s",home,input2+2)>=(int)sizeof(expanded))expanded[0]=0;
        }else if(input2[0]=='/')snprintf(expanded,sizeof(expanded),"%s",input2);
        else if(snprintf(expanded,sizeof(expanded),"%s/%s",home,input2)>=(int)sizeof(expanded))expanded[0]=0;
        struct stat st;
        if(*expanded){
            /* Allow entering a not-yet-created destination and browsing its parent. */
            while(*expanded && (stat(expanded,&st)!=0 || !S_ISDIR(st.st_mode))){
                char *slash=strrchr(expanded,'/');
                if(!slash)break;
                if(slash==expanded){expanded[1]=0;break;}
                *slash=0;
            }
            if(stat(expanded,&st)==0 && S_ISDIR(st.st_mode))snprintf(initial,sizeof(initial),"%s",expanded);
        }
    }
    int p[2];if(pipe(p)<0){notice("Couldn't launch folder picker.");return;}
    pid_t child=fork();if(child<0){close(p[0]);close(p[1]);return;}
    if(child==0){close(p[0]);dup2(p[1],STDOUT_FILENO);close(p[1]);
        execlp("kdialog","kdialog","--getexistingdirectory",initial,"--title","Choose any destination folder",(char*)NULL);
        char zenity_start[PATH_MAX+24];snprintf(zenity_start,sizeof(zenity_start),"--filename=%s/",initial);
        execlp("zenity","zenity","--file-selection","--directory",zenity_start,"--title=Choose destination folder",(char*)NULL);_exit(127);
    }
    close(p[1]);picker=child;picker_fd=p[0];picker_target=target;picker_len=0;
    fcntl(picker_fd,F_SETFL,fcntl(picker_fd,F_GETFL)|O_NONBLOCK);
    notice(target==1?"Choose any existing folder or drive; custom paths can also be typed.":"Opening folder picker...");
}
static void picker_poll(void){if(picker<=0)return;char buf[512];ssize_t n;
    while((n=read(picker_fd,buf,sizeof(buf)))>0){size_t z=(size_t)n;if(z>sizeof(picker_result)-1-picker_len)z=sizeof(picker_result)-1-picker_len;memcpy(picker_result+picker_len,buf,z);picker_len+=z;}
    int s;pid_t r=waitpid(picker,&s,WNOHANG);if(r!=picker)return;
    while((n=read(picker_fd,buf,sizeof(buf)))>0){size_t z=(size_t)n;if(z>sizeof(picker_result)-1-picker_len)z=sizeof(picker_result)-1-picker_len;memcpy(picker_result+picker_len,buf,z);picker_len+=z;}
    close(picker_fd);picker_fd=-1;picker=-1;picker_result[picker_len]=0;picker_result[strcspn(picker_result,"\r\n")]=0;
    if(WIFEXITED(s)&&WEXITSTATUS(s)==0&&*picker_result){
        if(picker_target==2){char portable[PATH_MAX];portable_home_path(picker_result,portable,sizeof(portable));
            size_t old=strlen(source_input),add=strlen(portable);
            if(old+add+2<sizeof(source_input)){if(old)source_input[old++]='|';strcpy(source_input+old,portable);set_focus(5);notice("Rule source added. Save Rule to apply.");}
            else notice("Too many source directories for this rule.");
        }else{snprintf(input2,sizeof(input2),"%s",picker_result);set_focus(2);notice("Folder chosen. Click ADD DIRECTORY or SAVE to apply.");}
    }
    else if(WIFEXITED(s)&&WEXITSTATUS(s)==127)notice("Install kdialog or zenity for Browse. You can type paths manually.");
    else notice("Folder selection canceled.");
}

/* Xdnd v5: accept local text/uri-list drops from Dolphin and other file managers.
 * Only the filename is used; dropped files are NEVER read, changed, or moved. */
static void dnd_reply(Atom msg,Window target,long a,long b,long c,long d){
    if(target==None)return;
    XEvent ev={0};
    ev.xclient.type=ClientMessage;ev.xclient.display=dpy;ev.xclient.window=target;
    ev.xclient.message_type=msg;ev.xclient.format=32;
    ev.xclient.data.l[0]=(long)(drag_reply_target!=None?drag_reply_target:win);
    ev.xclient.data.l[1]=a;ev.xclient.data.l[2]=b;ev.xclient.data.l[3]=c;ev.xclient.data.l[4]=d;
    XSendEvent(dpy,target,False,NoEventMask,&ev);XFlush(dpy);
}
static int hex_value(char c){
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
}
/* Only absolute local file URIs. Reject remote hosts, malformed escapes, NUL. */
static int decode_file_uri(const char *url,char *path,size_t cap){
    const char *src;
    if(!strncmp(url,"file://localhost/",17))src=url+16;
    else if(!strncmp(url,"file:///",8))src=url+7;
    else return 0;
    size_t n=0;
    for(;*src;src++){
        unsigned char c=(unsigned char)*src;
        if(c=='%'){
            int h=hex_value(src[1]);
            if(!src[1]||!src[2]||h<0||hex_value(src[2])<0)return 0;
            c=(unsigned char)(h*16+hex_value(src[2]));src+=2;
        }
        if(c==0||c<' '||c==127||n+1>=cap)return 0;
        path[n++]=(char)c;
    }
    path[n]=0;
    return n>1&&path[0]=='/';
}
static int extension_from_name(const char *filepath,char *pattern,size_t cap){
    const char *base=strrchr(filepath,'/');base=base?base+1:filepath;
    if(!*base||!strcmp(base,".")||!strcmp(base,".."))return 0;
    const char *ext=NULL;
    static const char *compound[]={".tar.gz",".tar.bz2",".tar.xz",".tar.zst",".tar.lz4",".tar.br"};
    size_t len=strlen(base);
    for(size_t i=0;i<sizeof(compound)/sizeof(compound[0]);i++){
        size_t n=strlen(compound[i]);
        if(len>n&&strcasecmp(base+len-n,compound[i])==0){ext=base+len-n+1;break;}
    }
    if(!ext){const char *dot=strrchr(base,'.');if(!dot||dot==base||!dot[1])return 0;ext=dot+1;}
    size_t n=strlen(ext);
    if(n+3>cap||n>MAX_PATTERN-2)return 0;
    for(size_t i=0;i<n;i++){
        unsigned char c=(unsigned char)ext[i];
        if(!(isalnum(c)||c=='.'||c=='-'||c=='_'))return 0;
    }
    if(snprintf(pattern,cap,"*.%s",ext)>=(int)cap)return 0;
    return 1;
}
static int use_sample_file(const char *filepath){
    struct stat st;
    if(stat(filepath,&st)!=0||!S_ISREG(st.st_mode))return 0;
    char pattern[MAX_PATTERN+1];
    if(!extension_from_name(filepath,pattern,sizeof(pattern)))return 0;
    tab=1;focus=0;
    for(int i=0;i<rule_count;i++){
        if(!strcmp(rules[i].pattern,pattern)&&!strcmp(rules[i].scope,"watch")){
            choose_rule(i);details_open=1;
            if(i<roffset)roffset=i;
            if(i>=roffset+SHOW_ROWS)roffset=i-SHOW_ROWS+1;
            char msg[512];snprintf(msg,sizeof(msg),"Already sorting %s. Existing rule selected; edit its destination if needed.",pattern);
            notice(msg);return 1;
        }
    }
    clear_rule_edit();
    snprintf(input1,sizeof(input1),"%s",pattern);
    input2[0]=0;details_open=1;focus=2;
    char msg[512];snprintf(msg,sizeof(msg),"Detected %s. Choose a destination and click SAVE RULE (sample untouched).",pattern);
    notice(msg);
    return 1;
}
static int use_dropped_destination(const char *filepath){
    struct stat st;
    if(tab!=1 || !details_open || stat(filepath,&st)!=0 || !S_ISDIR(st.st_mode))return 0;
    if(strlen(filepath)>=sizeof(input2))return 0;
    snprintf(input2,sizeof(input2),"%s",filepath);
    focus=2;
    notice("Destination folder selected. Click SAVE RULE to apply (nothing moved yet).");
    return 1;
}
static int parse_dropped_uri_list(const unsigned char *bytes,size_t len){
    if(!bytes||len==0||len>65536||memchr(bytes,0,len))return 0;
    char *copy=malloc(len+1);if(!copy)return 0;
    memcpy(copy,bytes,len);copy[len]=0;
    int accepted=0;char *save=NULL;
    for(char *line=strtok_r(copy,"\r\n",&save);line;line=strtok_r(NULL,"\r\n",&save)){
        if(!*line||*line=='#')continue;
        char path[PATH_MAX];
        if(decode_file_uri(line,path,sizeof(path)) && (use_dropped_destination(path)||use_sample_file(path))){accepted=1;break;}
    }
    free(copy);return accepted;
}
static void dnd_enter_event(XClientMessageEvent *e){
    drag_reply_target=e->window;
    drag_source=(Window)e->data.l[0];
    drag_version=((unsigned long)e->data.l[1]>>24)&255UL;
    drag_supported=0;drag_inside=0;drop_pending=0;
    if(drag_version<3||drag_version>5){redraw=1;return;}
    Atom offered[3]={None,None,None};
    if((e->data.l[1]&1)==0){
        for(int i=0;i<3;i++)offered[i]=(Atom)e->data.l[i+2];
        for(int i=0;i<3;i++)if(offered[i]==uri_list)drag_supported=1;
    }else{
        Atom actual;int fmt;unsigned long num,remaining;unsigned char *raw=NULL;
        if(XGetWindowProperty(dpy,drag_source,xdnd_typelist,0,64,False,XA_ATOM,
           &actual,&fmt,&num,&remaining,&raw)==Success){
            if(actual==XA_ATOM&&fmt==32&&raw){
                Atom *types=(Atom *)raw;
                for(unsigned long i=0;i<num;i++)if(types[i]==uri_list)drag_supported=1;
            }
        }
        if(raw)XFree(raw);
    }
    redraw=1;
}
static void dnd_position_event(XClientMessageEvent *e){
    if(drag_source==None||(Window)e->data.l[0]!=drag_source)return;
    drag_inside=drag_supported;
    dnd_reply(xdnd_status,drag_source,drag_supported?1:0,0,0,drag_supported?(long)xdnd_action_copy:0);
    redraw=1;
}
static void dnd_drop_event(XClientMessageEvent *e){
    if(drag_source==None||(Window)e->data.l[0]!=drag_source)return;
    drag_inside=0;redraw=1;
    if(!drag_supported){dnd_reply(xdnd_finished,drag_source,0,0,0,0);drag_source=None;return;}
    drop_pending=1;
    XConvertSelection(dpy,xdnd_selection,uri_list,xdnd_data,win,(Time)e->data.l[2]);
}
static void dnd_selection_event(XSelectionEvent *e){
    if(!drop_pending)return;
    int success=0;
    if(e->property==xdnd_data){
        Atom actual=None;int fmt=0;unsigned long n=0,remain=0;unsigned char *raw=NULL;
        int code=XGetWindowProperty(dpy,win,xdnd_data,0,16384,True,AnyPropertyType,
                                    &actual,&fmt,&n,&remain,&raw);
        if(code==Success&&actual==uri_list&&fmt==8&&remain==0&&n<=65536)
            success=parse_dropped_uri_list(raw,(size_t)n);
        if(raw)XFree(raw);
    }
    if(!success)notice("Drop ignored: use a local file, or a folder while editing a rule.");
    dnd_reply(xdnd_finished,drag_source,success?1:0,success?(long)xdnd_action_copy:0,0,0);
    drag_source=None;drag_supported=0;drop_pending=0;drag_inside=0;redraw=1;
}

static void paste(void){XConvertSelection(dpy,clip_atom,utf8_atom,clip_atom,win,CurrentTime);}
static void insert_edit_bytes(const char *data,size_t n,int clipboard){
    size_t cap=0;char *s=edit_buffer(focus,&cap);if(!s)return;
    size_t len=strlen(s);if(caret_offset>len)caret_offset=len;
    for(size_t i=0;i<n;i++){
        char ch=data[i];
        if(clipboard&&(ch=='\r'||ch=='\n'||ch=='\t'))break;
        if((unsigned char)ch<32||ch=='\t')continue;
        if((focus==3||focus==4)&&!(isdigit((unsigned char)ch)||(focus==3&&ch=='.')))continue;
        if(len+1>=cap)break;
        memmove(s+caret_offset+1,s+caret_offset,len-caret_offset+1);
        s[caret_offset++]=ch;len++;
    }
    redraw=1;
}
static void clipboard_event(XSelectionEvent *e){if(e->property==None||focus<1)return;
    Atom typ;int fmt;unsigned long count,remain;unsigned char *data=NULL;
    if(XGetWindowProperty(dpy,win,clip_atom,0,PATH_MAX,True,AnyPropertyType,&typ,&fmt,&count,&remain,&data)==Success&&data){
        if(fmt==8&&remain==0)insert_edit_bytes((const char*)data,(size_t)count,1);
        XFree(data);
    }
}
static void key_event(XKeyEvent *e){KeySym sym;char buf[100];int n=XLookupString(e,buf,sizeof(buf),&sym,NULL);
    if((e->state&ControlMask)&&(sym==XK_m||sym==XK_M)){
        if(!fs_menu_show(dpy,win))notice("No launcher available. Open the AppImage menu.");return;
    }
    if((e->state&ControlMask)&&(sym==XK_1||sym==XK_2)){
        tab=(sym==XK_1)?0:1;focus=0;row_hover=-1;redraw=1;return;
    }
    if((e->state&ControlMask)&&(sym==XK_r||sym==XK_R)){
        reload_files();redraw=1;return;
    }
    if(sym==XK_Escape){focus=0;redraw=1;return;}
    if(sym==XK_Tab){if(tab==0)set_focus(2);else if(!details_open)set_focus(1);
        else if(details_page==0)set_focus(focus==1?2:1);else set_focus(focus==1?5:1);return;}
    if(focus==0){
        if(sym==XK_Up||sym==XK_Down){
            int count=tab==0?dir_count:rule_count;
            if(count>0){int current=tab==0?selected_dir:selected_rule;
                int next=current+(sym==XK_Down?1:-1);
                if(current<0)next=0;if(next<0)next=0;if(next>=count)next=count-1;
                if(tab==0){choose_directory(next);if(next<doffset)doffset=next;else if(next>=doffset+SHOW_ROWS)doffset=next-SHOW_ROWS+1;}
                else{choose_rule(next);if(next<roffset)roffset=next;else if(next>=roffset+SHOW_ROWS)roffset=next-SHOW_ROWS+1;}
                focus=0;redraw=1;
            }return;
        }
        if(sym==XK_Delete){if(tab==0)remove_directory();else remove_rule();}return;
    }
    if((e->state&ControlMask)&&(sym==XK_v||sym==XK_V)){paste();return;}
    if(focus==3&&(sym==XK_Up||sym==XK_Down)){step_interval(sym==XK_Up?1:-1);caret_offset=strlen(interval_input);return;}
    if(sym==XK_Return||sym==XK_KP_Enter){if(focus==3)save_interval();else if(tab==0)add_directory();else save_rule_edit();return;}
    size_t cap=0;char *s=edit_buffer(focus,&cap);if(!s)return;
    size_t len=strlen(s);if(caret_offset>len)caret_offset=len;
    if(sym==XK_Left){if(caret_offset)caret_offset--;redraw=1;return;}
    if(sym==XK_Right){if(caret_offset<len)caret_offset++;redraw=1;return;}
    if(sym==XK_Home){caret_offset=0;redraw=1;return;}
    if(sym==XK_End){caret_offset=len;redraw=1;return;}
    if(sym==XK_BackSpace){if(caret_offset){memmove(s+caret_offset-1,s+caret_offset,len-caret_offset+1);caret_offset--;}redraw=1;return;}
    if(sym==XK_Delete){if(caret_offset<len)memmove(s+caret_offset,s+caret_offset+1,len-caret_offset);redraw=1;return;}
    if((e->state&ControlMask)&&(sym==XK_a||sym==XK_A)){s[0]=0;caret_offset=0;redraw=1;return;}
    if(n>0&&!(e->state&ControlMask))insert_edit_bytes(buf,(size_t)n,0);
}
static void scroll_list(int delta){int *off=tab==0?&doffset:&roffset;int count=tab==0?dir_count:rule_count;int max=count>SHOW_ROWS?count-SHOW_ROWS:0;*off+=delta;if(*off<0)*off=0;if(*off>max)*off=max;redraw=1;}
static void click_event(int x,int y,unsigned int button_id){
    if(button_id==1 && in_rect(x,y,915,22,190,42)){if(!fs_menu_show(dpy,win))notice("No launcher available. Relaunch the AppImage to open its menu.");return;}
    if(button_id==4||button_id==5){if(x<LIST_X+LIST_W)scroll_list(button_id==4?-2:2);return;}
    if(button_id!=1)return;
    if(in_rect(x,y,200,153,109,29)){set_focus(3);return;}
    if(in_rect(x,y,317,153,46,14)){step_interval(1);return;}
    if(in_rect(x,y,317,168,46,14)){step_interval(-1);return;}
    if(in_rect(x,y,374,153,80,29)){save_interval();return;}
    if(in_rect(x,y,825,152,279,31)){toggle_overwrite();return;}
    if(in_rect(x,y,25,96,234,42)){tab=0;focus=0;input1[0]=input2[0]=0;redraw=1;return;}
    if(in_rect(x,y,269,96,234,42)){tab=1;focus=0;input1[0]=input2[0]=0;selected_rule=-1;details_open=0;redraw=1;return;}
    if(in_rect(x,y,530,96,170,42)){su_toggle_auto();redraw=1;return;}
    if(in_rect(x,y,713,96,200,42)){su_launch(0);return;}
    if(in_rect(x,y,930,96,175,42)){reload_files();return;}
    if(tab==0){
        if(in_rect(x,y,LIST_X,LIST_Y,LIST_W,ROW_HEIGHT*SHOW_ROWS)){int i=doffset+(y-LIST_Y)/ROW_HEIGHT;if(i<dir_count)choose_directory(i);return;}
        if(in_rect(x,y,37,583,159,35)){scroll_list(-SHOW_ROWS);return;}
        if(in_rect(x,y,204,583,159,35)){scroll_list(SHOW_ROWS);return;}
        if(in_rect(x,y,748,273,340,43)){set_focus(2);return;}
        if(in_rect(x,y,748,340,340,44)){picker_open(0);return;}
        if(in_rect(x,y,748,404,340,46)){add_directory();return;}
        if(in_rect(x,y,748,464,340,46)){remove_directory();return;}
        if(in_rect(x,y,748,512,166,25)){add_suggestion("Downloads");return;}
        if(in_rect(x,y,922,512,166,25)){add_suggestion("Documents");return;}
        if(in_rect(x,y,748,547,340,34)){toggle_destination_mode();return;}
    }else{
        if(in_rect(x,y,LIST_X,253,LIST_W,ROW_HEIGHT*SHOW_ROWS)){int i=roffset+(y-253)/ROW_HEIGHT;if(i<rule_count){
            choose_rule(i);if(x>=37&&x<63){rules[i].recursive=!rules[i].recursive;recursive_input=rules[i].recursive;
                if(save_rules()==0)notice(recursive_input?"Search subfolders enabled for this rule.":"Search subfolders disabled for this rule.");else notice("ERROR saving recursive rule setting.");}
            else if(x>=69&&x<95){
                if(!rules[i].overwrite&&confirm_overwrite_rule!=i){confirm_overwrite_rule=i;
                    notice("WARNING: overwriting cannot be undone. Click [!] AGAIN to enable for this rule.");redraw=1;}
                else{rules[i].overwrite=!rules[i].overwrite;overwrite_input=rules[i].overwrite;confirm_overwrite_rule=-1;
                    if(save_rules()==0)notice(overwrite_input?"Overwrite enabled for this rule.":"Overwrite disabled for this rule.");else notice("ERROR saving overwrite setting.");}
            }
        }return;}
        if(in_rect(x,y,32,582,120,35)){scroll_list(-SHOW_ROWS);return;}
        if(in_rect(x,y,159,582,120,35)){scroll_list(SHOW_ROWS);return;}
        if(in_rect(x,y,287,582,120,35)){shift_rule(-1);return;}
        if(in_rect(x,y,415,582,120,35)){shift_rule(1);return;}
        if(in_rect(x,y,748,259,340,41)){set_focus(1);return;}
        if(in_rect(x,y,748,333,340,36)){details_open=!details_open;if(!details_open && focus>=2 && focus!=3)focus=0;redraw=1;return;}
        if(details_open){
            if(in_rect(x,y,748,376,165,25)){details_page=0;focus=0;redraw=1;return;}
            if(in_rect(x,y,920,376,168,25)){details_page=1;focus=0;redraw=1;return;}
            if(details_page==0){
                if(in_rect(x,y,748,410,242,38)){set_focus(2);return;}
                if(in_rect(x,y,996,410,92,38)){picker_open(1);return;}
                if(in_rect(x,y,748,473,340,36)){scope_index=(scope_index+1)%3;redraw=1;return;}
                if(in_rect(x,y,748,529,340,35)){mode_index=(mode_index+1)%2;redraw=1;return;}
            }else{
                if(in_rect(x,y,748,454,340,25)){recursive_input=!recursive_input;redraw=1;return;}
                if(in_rect(x,y,748,482,340,25)){overwrite_input=!overwrite_input;
                    notice(overwrite_input?"WARNING: saving this rule will allow replacing same-named files.":"Overwrite disabled for this rule after saving.");redraw=1;return;}
                if(in_rect(x,y,748,526,340,26)){set_focus(5);return;}
                if(in_rect(x,y,748,554,164,24)){picker_open(2);return;}
                if(in_rect(x,y,920,554,168,24)){source_input[0]=0;set_focus(5);return;}
            }
        }
        if(in_rect(x,y,748,583,111,37)){clear_rule_edit();return;}
        if(in_rect(x,y,866,583,106,37)){save_rule_edit();return;}
        if(in_rect(x,y,980,583,108,37)){remove_rule();return;}
        if(in_rect(x,y,926,662,171,28)){reset_rules();return;}
    }
}
int main(int argc,char **argv){
    const char *h=getenv("HOME");if(!h||h[0]!='/'){fputs("HOME must be an absolute path.\n",stderr);return 1;}snprintf(home,sizeof(home),"%s",h);
    const char *xdg=getenv("XDG_CONFIG_HOME");char cfg[PATH_MAX];if(xdg&&*xdg=='/')snprintf(cfg,sizeof(cfg),"%s/sorter-config",xdg);else snprintf(cfg,sizeof(cfg),"%s/.config/sorter-config",home);
    if(strlen(cfg)+25>=PATH_MAX){fputs("Config path too long\n",stderr);return 1;}
    snprintf(dir_file,sizeof(dir_file),"%s/directories.txt",cfg);snprintf(rules_file,sizeof(rules_file),"%s/rules.tsv",cfg);snprintf(overwrite_file,sizeof(overwrite_file),"%s/overwrite-files.txt",cfg);snprintf(scan_interval_file,sizeof(scan_interval_file),"%s/scan-interval.txt",cfg);snprintf(destination_mode_file,sizeof(destination_mode_file),"%s/destination-mode.txt",cfg);load_overwrite();load_interval();load_destination_mode();
    su_initialize();
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--help")){puts("File Sorter Config GUI v1.3.12\nUsage: Sorter.Config [--dump-config]\nEdits ~/.config/sorter-config/{directories.txt,rules.tsv}");return 0;}
        if(!strcmp(argv[i],"--dump-config")){load_directories();load_rules();printf("Monitored directories: %d\nSorting rules: %d\nDirectories file: %s\nRules file: %s\n",dir_count,rule_count,dir_file,rules_file);return 0;}
    }
    notice("Changes are saved immediately and picked up by the sorter on its next scan.");load_directories();load_rules();load_destination_mode();
    signal(SIGTERM,on_signal);signal(SIGINT,on_signal);
    dpy=XOpenDisplay(NULL);if(!dpy){fputs("Cannot open an X11 graphical display. Run in Steam Deck Desktop Mode.\n",stderr);return 1;}
    screen=DefaultScreen(dpy);bg=color("#101722");panel=color("#1c2938");header=color("#303d4b");ink=color("#edf4ff");muted=color("#a9bacb");green=color("#2c9c78");orange=color("#efbe77");blue=color("#365c91");red=color("#b64d5f");line=color("#2f4358");active=color("#2e506c");(void)orange;
    Window parent=fs_menu_parent(dpy);
    win=XCreateSimpleWindow(dpy,parent,fs_menu_launcher==None?68:0,
                            fs_menu_launcher==None?44:0,W,H,0,bg,bg);
    XStoreName(dpy,win,"File Sorter - Configuration Editor");
    fs_apply_x11_window_icon(dpy, win);
    XSelectInput(dpy,win,ExposureMask|ButtonPressMask|KeyPressMask|PointerMotionMask|LeaveWindowMask|StructureNotifyMask);
    wm_delete=XInternAtom(dpy,"WM_DELETE_WINDOW",False);
    if(fs_menu_launcher==None)XSetWMProtocols(dpy,win,&wm_delete,1);
    clip_atom=XInternAtom(dpy,"CLIPBOARD",False);utf8_atom=XInternAtom(dpy,"UTF8_STRING",False);
    xdnd_aware=XInternAtom(dpy,"XdndAware",False);
    xdnd_enter=XInternAtom(dpy,"XdndEnter",False);
    xdnd_position=XInternAtom(dpy,"XdndPosition",False);
    xdnd_status=XInternAtom(dpy,"XdndStatus",False);
    xdnd_leave=XInternAtom(dpy,"XdndLeave",False);
    xdnd_drop=XInternAtom(dpy,"XdndDrop",False);
    xdnd_finished=XInternAtom(dpy,"XdndFinished",False);
    xdnd_selection=XInternAtom(dpy,"XdndSelection",False);
    xdnd_typelist=XInternAtom(dpy,"XdndTypeList",False);
    xdnd_action_copy=XInternAtom(dpy,"XdndActionCopy",False);
    xdnd_data=XInternAtom(dpy,"GENERAL_CLEANUP_XDND_DATA",False);
    uri_list=XInternAtom(dpy,"text/uri-list",False);
    incr_atom=XInternAtom(dpy,"INCR",False);
    unsigned long xdnd_version=5;
    XChangeProperty(dpy,win,xdnd_aware,XA_ATOM,32,PropModeReplace,
                    (unsigned char *)&xdnd_version,1);
    if(fs_menu_launcher==None){XSizeHints hints={0};hints.flags=PMinSize|PMaxSize;
    hints.min_width=W;hints.max_width=W;hints.min_height=H;hints.max_height=H;
    XSetWMNormalHints(dpy,win,&hints);}
    pointer_cursor=XCreateFontCursor(dpy,XC_hand2);text_cursor=XCreateFontCursor(dpy,XC_xterm);
    gc=XCreateGC(dpy,win,0,NULL);font=XLoadQueryFont(dpy,"9x15");if(!font)font=XLoadQueryFont(dpy,"fixed");bigfont=XLoadQueryFont(dpy,"10x20");
    XMapWindow(dpy,win);
    fs_menu_register(dpy,win,"FILE_SORTER_CONFIG_WINDOW");
    if(su_auto_enabled)su_launch(1);
    while(!exiting){
        while(XPending(dpy)&&!exiting){XEvent ev;XNextEvent(dpy,&ev);
            if(ev.type==Expose)redraw=1;
            else if(ev.type==MotionNotify){
                int x=ev.xmotion.x,y=ev.xmotion.y;
                int h=(x>=LIST_X&&x<LIST_X+LIST_W&&y>=(tab?253:LIST_Y)&&y<(tab?253:LIST_Y)+ROW_HEIGHT*SHOW_ROWS)?
                    ((tab?roffset:doffset)+(y-(tab?253:LIST_Y))/ROW_HEIGHT):-1;
                if(h>=(tab?rule_count:dir_count))h=-1;
                if(x!=mouse_x||y!=mouse_y||h!=row_hover){mouse_x=x;mouse_y=y;row_hover=h;redraw=1;}
            }
            else if(ev.type==LeaveNotify){mouse_x=mouse_y=-1;row_hover=-1;redraw=1;}
            else if(ev.type==ButtonPress)click_event(ev.xbutton.x,ev.xbutton.y,ev.xbutton.button);
            else if(ev.type==KeyPress)key_event(&ev.xkey);
            else if(ev.type==SelectionNotify){
                if(ev.xselection.selection==xdnd_selection)dnd_selection_event(&ev.xselection);
                else clipboard_event(&ev.xselection);
            }
            else if(ev.type==ClientMessage){
                if(ev.xclient.message_type==xdnd_enter)dnd_enter_event(&ev.xclient);
                else if(ev.xclient.message_type==xdnd_position)dnd_position_event(&ev.xclient);
                else if(ev.xclient.message_type==xdnd_drop)dnd_drop_event(&ev.xclient);
                else if(ev.xclient.message_type==xdnd_leave){
                    if((Window)ev.xclient.data.l[0]==drag_source){drag_source=None;drag_supported=0;drag_inside=0;drop_pending=0;redraw=1;}
                }
                else if((Atom)ev.xclient.data.l[0]==wm_delete)exiting=1;
            }
            else if(ev.type==DestroyNotify)exiting=1;
        }
        picker_poll();su_poll();if(focus)redraw=1;if(redraw)render();struct timespec t={.tv_sec=0,.tv_nsec=70000000};nanosleep(&t,NULL);
    }
    su_cleanup();
    if(picker>0){kill(picker,SIGTERM);waitpid(picker,NULL,0);}if(picker_fd>=0)close(picker_fd);
    XFreeCursor(dpy,pointer_cursor);XFreeCursor(dpy,text_cursor);if(font)XFreeFont(dpy,font);if(bigfont)XFreeFont(dpy,bigfont);XFreeGC(dpy,gc);XDestroyWindow(dpy,win);XCloseDisplay(dpy);return 0;
}
