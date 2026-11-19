#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 700
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xatom.h>
#include <X11/keysym.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define W 790
#define H 468
static Display *dpy;
static Window win;
static GC gc;
static int screen;
static Atom wm_delete;
static unsigned long bg, panel, accent, ink, subtle, border;
static char status_msg[512] = "Choose an application to open.";
static char appdir[PATH_MAX];
static XFontStruct *small, *large;
static int needs_redraw=1;
static pid_t sorter_child=-1, config_child=-1;
static void draw_status(const char *msg);
static int x11_recoverable_error(Display *display, XErrorEvent *event){
    (void)display;(void)event;return 0;
}
static void child_exited_impl(pid_t *slot, const char *name){
    if(*slot<=0)return;
    int status;pid_t result=waitpid(*slot,&status,WNOHANG);
    if(result==*slot || (result<0 && errno==ECHILD)){
        *slot=-1;
        if(name)draw_status(name);
    }
}

static void draw_status(const char *msg){snprintf(status_msg,sizeof(status_msg),"%s",msg);needs_redraw=1;}
#define UPDATE_NOTIFY(message) draw_status(message)
#include "sorter_update.h"

static unsigned long color(const char *hex){XColor exact,actual;return XAllocNamedColor(dpy,DefaultColormap(dpy,screen),hex,&actual,&exact)?actual.pixel:WhitePixel(dpy,screen);}
static void rect(int x,int y,int w,int h,unsigned long c){XSetForeground(dpy,gc,c);XFillRectangle(dpy,win,gc,x,y,w,h);}
static void label(int x,int y,const char *str,unsigned long c,int title){XSetForeground(dpy,gc,c);if(title&&large)XSetFont(dpy,gc,large->fid);else if(small)XSetFont(dpy,gc,small->fid);XDrawString(dpy,win,gc,x,y,str,(int)strlen(str));}
static void btn(int y,const char *title,const char *subtitle,int emphasized){
    rect(32,y,W-64,88,emphasized?accent:panel);
    label(54,y+32,title,ink,1);
    label(54,y+63,subtitle,emphasized?ink:subtle,0);
    label(W-74,y+51,">",ink,1);
}
static void redraw(void){
    rect(0,0,W,H,bg);rect(0,0,W,6,accent);
    label(32,53,"FILE SORTER",ink,1);
    label(33,78,"v1.2.1  |  Linux x86-64 AppImage  |  Closing launcher exits all apps",subtle,0);
    btn(103,"START SORTER","Open or return to the sorter. Back to Menu keeps sorting active.",1);
    btn(202,"CONFIGURE","Open or return to your existing configuration window",0);
    btn(301,"CHECK FOR UPDATES","Check the newest GitHub release and update this AppImage",0);
    rect(0,H-58,W,58,panel);
    label(28,H-25,status_msg,ink,0);
    XFlush(dpy);needs_redraw=0;
}
static Window child_window(const char *slot){
    Atom prop=XInternAtom(dpy,slot,False),actual=None;
    int format=0;unsigned long count=0,extra=0;unsigned char *data=NULL;
    if(XGetWindowProperty(dpy,win,prop,0,1,False,XA_WINDOW,&actual,&format,&count,&extra,&data)!=Success)
        return None;
    Window child=None;
    if(actual==XA_WINDOW && format==32 && count==1 && data)
        child=(Window)(*(unsigned long*)data);
    if(data)XFree(data);
    return child;
}
static void open_program(const char *name){
    const int is_sorter=strcmp(name,"Sorter")==0;
    pid_t *pid=is_sorter?&sorter_child:&config_child;
    const char *slot=is_sorter?"FILE_SORTER_SORTER_WINDOW":"FILE_SORTER_CONFIG_WINDOW";
    child_exited_impl(pid,NULL);
    if(*pid>0){
        Window child=child_window(slot);
        if(child!=None){
            XWindowAttributes attrs;
            if(XGetWindowAttributes(dpy,child,&attrs)){
                XMapRaised(dpy,child);
                XFlush(dpy);
                draw_status(is_sorter?"Returned to running Sorter.":"Returned to open Config editor.");
                return;
            }
        }
        draw_status("Application is still starting. Please try again.");
        return;
    }
    char path[PATH_MAX], xid[32];
    if(snprintf(path,sizeof(path),"%s/usr/bin/%s",appdir,name)>=(int)sizeof(path)){
        draw_status("Application path too long.");return;
    }
    snprintf(xid,sizeof(xid),"0x%lx",(unsigned long)win);
    pid_t child=fork();
    if(child<0){draw_status("Unable to launch application.");return;}
    if(child==0){
        setenv("FILE_SORTER_LAUNCHER_XID",xid,1);
        execl(path,name,(char*)NULL);
        _exit(127);
    }
    *pid=child;
    draw_status(is_sorter?"Sorter opened. Use BACK TO MENU to return here.":
                          "Config editor opened. Use BACK TO MENU to return here.");
}

int main(void){
    const char *root=getenv("APPDIR");
    if(!root||root[0]!='/'){
        char exe[PATH_MAX];ssize_t len=readlink("/proc/self/exe",exe,sizeof(exe)-1);
        if(len<=0){fputs("No AppDir found.\n",stderr);return 1;}
        exe[len]=0;
        char *pos=strstr(exe,"/usr/bin/");
        if(!pos){fputs("Launch using AppRun.\n",stderr);return 1;}
        *pos=0;snprintf(appdir,sizeof(appdir),"%s",exe);
    }else if(snprintf(appdir,sizeof(appdir),"%s",root)>=(int)sizeof(appdir))return 1;
    dpy=XOpenDisplay(NULL);
    if(!dpy){fputs("An X11/XWayland desktop is required.\n",stderr);return 1;}
    XSetErrorHandler(x11_recoverable_error);
    screen=DefaultScreen(dpy);
    win=XCreateSimpleWindow(dpy,RootWindow(dpy,screen),180,100,W,H,0,0,0);
    XStoreName(dpy,win,"File Sorter - Launcher v1.2.1");
    wm_delete=XInternAtom(dpy,"WM_DELETE_WINDOW",False);XSetWMProtocols(dpy,win,&wm_delete,1);
    XSelectInput(dpy,win,ExposureMask|ButtonPressMask|KeyPressMask|StructureNotifyMask);
    gc=XCreateGC(dpy,win,0,NULL);
    bg=color("#131a27");panel=color("#243044");accent=color("#225d63");ink=color("#f3f6fc");subtle=color("#c0cadb");border=color("#314054");(void)border;
    small=XLoadQueryFont(dpy,"-misc-fixed-medium-r-normal--14-*-*-*-*-*-iso8859-1");
    large=XLoadQueryFont(dpy,"-misc-fixed-bold-r-normal--18-*-*-*-*-*-iso8859-1");
    if(!small)small=XLoadQueryFont(dpy,"fixed");
    if(!large)large=small;
    XMapWindow(dpy,win);
    su_initialize();
    int running=1;
    while(running){
        while(XPending(dpy)){
            XEvent event;XNextEvent(dpy,&event);
            if(event.type==ClientMessage&&(Atom)event.xclient.data.l[0]==wm_delete){running=0;break;}
            if(event.type==Expose)needs_redraw=1;
            if(event.type==ButtonPress){int y=event.xbutton.y,x=event.xbutton.x;
                if(x>=32&&x<W-32&&y>=103&&y<191)open_program("Sorter");
                else if(x>=32&&x<W-32&&y>=202&&y<290)open_program("Sorter.Config");
                else if(x>=32&&x<W-32&&y>=301&&y<389)su_launch(0);
            }
            if(event.type==KeyPress){KeySym key=XLookupKeysym(&event.xkey,0);
                if(key==XK_Escape)running=0;
                else if(key==XK_1)open_program("Sorter");
                else if(key==XK_2)open_program("Sorter.Config");
                else if(key==XK_3)su_launch(0);
            }
        }
        child_exited_impl(&sorter_child,"Sorter window closed. Main menu is ready.");
        child_exited_impl(&config_child,"Config editor closed. Main menu is ready.");
        su_poll();
        if(needs_redraw)redraw();
        struct timespec nap={0,70000000};nanosleep(&nap,NULL);
    }
    /* Closing the launcher ends its child GUIs as well. That prevents an
       invisible sorter process from remaining active after the menu exits. */
    if(sorter_child>0)kill(sorter_child,SIGTERM);
    if(config_child>0)kill(config_child,SIGTERM);
    if(sorter_child>0)waitpid(sorter_child,NULL,0);
    if(config_child>0)waitpid(config_child,NULL,0);
    su_cleanup();XFreeGC(dpy,gc);XDestroyWindow(dpy,win);XCloseDisplay(dpy);return 0;
}
