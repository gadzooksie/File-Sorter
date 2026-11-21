#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 700
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xatom.h>
#include "file_sorter_icon_x11.h"
#include <X11/keysym.h>
#include <X11/cursorfont.h>
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

#define W 1130
#define H 714
static Display *dpy;
static Window win;
static GC gc;
static int screen;
static Atom wm_delete;
static unsigned long bg, panel, accent, ink, subtle, border, hover_color, hover_outline, focus_outline;
static char status_msg[512] = "Choose an application to open.";
static char appdir[PATH_MAX];
static XFontStruct *small, *large;
static int needs_redraw=1;
static pid_t sorter_child=-1, config_child=-1;
/* 0 = menu, 1 = sorter, 2 = configuration editor. */
static int active_page=0;
static int focus_card=0,hover_card=-1;
static Cursor hand_cursor;
static Atom navigate_atom,sorter_atom,config_atom;
static Atom xdnd_aware,xdnd_enter,xdnd_position,xdnd_drop,xdnd_leave;
static void show_page(int page);
static Window child_window(const char *slot);
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
static void btn(int y,const char *title,const char *subtitle,int emphasized,int index){
    int hot=hover_card==index,focused=focus_card==index;
    rect(64,y,W-128,105,hot?hover_color:(emphasized?accent:panel));
    if(hot||focused){
        XSetForeground(dpy,gc,hot?hover_outline:focus_outline);
        XDrawRectangle(dpy,win,gc,64,y,W-129,104);
        rect(64,y,5,105,hot?hover_outline:focus_outline);
    }
    label(96,y+43,title,ink,1);
    label(96,y+76,subtitle,hot||emphasized?ink:subtle,0);
    label(W-98,y+60,">",ink,1);
}
static void redraw(void){
    rect(0,0,W,H,bg);
    rect(0,0,W,6,accent);
    if(active_page!=0){
        if(active_page==1)
            label(18,19,"FILE SORTER  /  SORTER",subtle,0);
        XFlush(dpy);needs_redraw=0;
        return;
    }
    label(64,95,"FILE SORTER",ink,1);
    label(65,128,"v1.3.7  |  Linux x86-64 AppImage  |  One window, three pages",subtle,0);
    btn(167,"START SORTER","Open or return to your running sorter. Sorting continues when you go back.",1,0);
    btn(308,"CONFIGURE","Manage monitored folders, formats and destinations in this same window.",0,1);
    btn(449,"CHECK FOR UPDATES","Check GitHub for a new version of this AppImage",0,2);
    label(66,584,"TIP: Tab selects a card, Enter opens it, 1/2/3 jump directly.",subtle,0);
    rect(0,H-72,W,72,panel);
    label(58,H-31,status_msg,ink,0);
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
static void show_page(int page){
    if(page<0||page>2)return;
    Window old=None,next=None;
    if(active_page==1)old=child_window("FILE_SORTER_SORTER_WINDOW");
    else if(active_page==2)old=child_window("FILE_SORTER_CONFIG_WINDOW");
    if(old!=None)XUnmapWindow(dpy,old);
    active_page=page;
    if(page==0){
        XStoreName(dpy,win,"File Sorter v1.3.7");
        XSetInputFocus(dpy,win,RevertToParent,CurrentTime);
    }else{
        next=child_window(page==1?"FILE_SORTER_SORTER_WINDOW":"FILE_SORTER_CONFIG_WINDOW");
        XStoreName(dpy,win,page==1?"File Sorter v1.3.7 - Sorter":"File Sorter v1.3.7 - Config");
        if(next!=None){
            XWindowAttributes attrs;
            if(XGetWindowAttributes(dpy,next,&attrs)){
                XMapRaised(dpy,next);
                XSetInputFocus(dpy,next,RevertToParent,CurrentTime);
            }
        }
    }
    /* DnD clients can send Xdnd messages to the WM toplevel shell.
       Forward to Config, preserving the shell's target window ID. */
    if(page==2){
        unsigned long version=5;
        XChangeProperty(dpy,win,xdnd_aware,XA_ATOM,32,PropModeReplace,
                        (unsigned char*)&version,1);
    }else XDeleteProperty(dpy,win,xdnd_aware);
    needs_redraw=1;
    XFlush(dpy);
}
static void open_program(const char *name){
    int is_sorter=strcmp(name,"Sorter")==0;
    int page=is_sorter?1:2;
    pid_t *pid=is_sorter?&sorter_child:&config_child;
    const char *slot=is_sorter?"FILE_SORTER_SORTER_WINDOW":"FILE_SORTER_CONFIG_WINDOW";
    child_exited_impl(pid,NULL);
    if(*pid>0){
        Window child=child_window(slot);
        if(child!=None){
            show_page(page);
            draw_status(is_sorter?"Returned to running Sorter.":"Returned to your open Config editor.");
            return;
        }
        show_page(page);
        draw_status("Application is still starting...");
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
        setenv("FILE_SORTER_EMBED_PARENT",xid,1);
        execl(path,name,(char*)NULL);
        _exit(127);
    }
    *pid=child;
    show_page(page);
    draw_status(is_sorter?"Sorter open. Back to Menu keeps it sorting.":
                          "Config editor open. Use Back to Menu to switch pages.");
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
    win=XCreateSimpleWindow(dpy,RootWindow(dpy,screen),100,70,W,H,0,0,0);
    XStoreName(dpy,win,"File Sorter v1.3.7");
    fs_apply_x11_window_icon(dpy, win);
    navigate_atom=XInternAtom(dpy,"FILE_SORTER_NAVIGATE",False);
    sorter_atom=XInternAtom(dpy,"FILE_SORTER_SORTER_WINDOW",False);
    config_atom=XInternAtom(dpy,"FILE_SORTER_CONFIG_WINDOW",False);
    xdnd_aware=XInternAtom(dpy,"XdndAware",False);
    xdnd_enter=XInternAtom(dpy,"XdndEnter",False);
    xdnd_position=XInternAtom(dpy,"XdndPosition",False);
    xdnd_drop=XInternAtom(dpy,"XdndDrop",False);
    xdnd_leave=XInternAtom(dpy,"XdndLeave",False);
    wm_delete=XInternAtom(dpy,"WM_DELETE_WINDOW",False);XSetWMProtocols(dpy,win,&wm_delete,1);
    XSelectInput(dpy,win,ExposureMask|ButtonPressMask|KeyPressMask|PointerMotionMask|LeaveWindowMask|
                         StructureNotifyMask|PropertyChangeMask);
    XSizeHints hints={0};hints.flags=PMinSize|PMaxSize;
    hints.min_width=W;hints.max_width=W;hints.min_height=H;hints.max_height=H;
    XSetWMNormalHints(dpy,win,&hints);
    gc=XCreateGC(dpy,win,0,NULL);
    bg=color("#131a27");panel=color("#243044");accent=color("#225d63");ink=color("#f3f6fc");subtle=color("#c0cadb");border=color("#314054");hover_color=color("#396e80");hover_outline=color("#8de2e6");focus_outline=color("#769fcb");(void)border;
    small=XLoadQueryFont(dpy,"-misc-fixed-medium-r-normal--14-*-*-*-*-*-iso8859-1");
    large=XLoadQueryFont(dpy,"-misc-fixed-bold-r-normal--18-*-*-*-*-*-iso8859-1");
    if(!small)small=XLoadQueryFont(dpy,"fixed");
    if(!large)large=small;
    hand_cursor=XCreateFontCursor(dpy,XC_hand2);
    XMapWindow(dpy,win);
    su_initialize();
    int running=1;
    while(running){
        while(XPending(dpy)){
            XEvent event;XNextEvent(dpy,&event);
            if(event.type==ClientMessage&&event.xclient.window==win&&
                event.xclient.message_type==navigate_atom){
                Window sender=(Window)event.xclient.data.l[1];
                Window expected=active_page==1?child_window("FILE_SORTER_SORTER_WINDOW"):
                                active_page==2?child_window("FILE_SORTER_CONFIG_WINDOW"):None;
                if(event.xclient.data.l[0]==0 && expected!=None && sender==expected){
                    show_page(0);
                    draw_status("Main menu ready. Your open applications retain their state.");
                }
                continue;
            }
            if(event.type==ClientMessage&&event.xclient.window==win&&
                ((event.xclient.message_type==xdnd_enter)||
                 (event.xclient.message_type==xdnd_position)||
                 (event.xclient.message_type==xdnd_drop)||
                 (event.xclient.message_type==xdnd_leave))){
                Window target=active_page==2?child_window("FILE_SORTER_CONFIG_WINDOW"):None;
                if(target!=None)XSendEvent(dpy,target,False,NoEventMask,&event);
                XFlush(dpy);
                continue;
            }
            if(event.type==ClientMessage&&event.xclient.window==win&&
                (Atom)event.xclient.data.l[0]==wm_delete){running=0;break;}
            if(event.type==PropertyNotify && event.xproperty.window==win&&
               (event.xproperty.atom==sorter_atom||event.xproperty.atom==config_atom)){
                int page=event.xproperty.atom==sorter_atom?1:2;
                Window child=child_window(page==1?"FILE_SORTER_SORTER_WINDOW":
                                             "FILE_SORTER_CONFIG_WINDOW");
                if(child!=None){
                    if(active_page==page)show_page(page);
                    else XUnmapWindow(dpy,child);
                }
            }
            if(event.type==Expose&&event.xexpose.window==win)needs_redraw=1;
            if(event.type==MotionNotify&&event.xmotion.window==win&&active_page==0){
                int x=event.xmotion.x,y=event.xmotion.y,hit=-1;
                if(x>=64&&x<W-64){if(y>=167&&y<272)hit=0;else if(y>=308&&y<413)hit=1;else if(y>=449&&y<554)hit=2;}
                if(hit!=hover_card){hover_card=hit;needs_redraw=1;
                    if(hit>=0)XDefineCursor(dpy,win,hand_cursor);else XUndefineCursor(dpy,win);}
            }
            if(event.type==LeaveNotify&&event.xcrossing.window==win&&hover_card>=0){
                hover_card=-1;XUndefineCursor(dpy,win);needs_redraw=1;
            }
            if(event.type==ButtonPress&&event.xbutton.window==win&&active_page==0){
                int y=event.xbutton.y,x=event.xbutton.x;
                if(x>=64&&x<W-64&&y>=167&&y<272){focus_card=0;open_program("Sorter");}
                else if(x>=64&&x<W-64&&y>=308&&y<413){focus_card=1;open_program("Sorter.Config");}
                else if(x>=64&&x<W-64&&y>=449&&y<554){focus_card=2;su_launch(0);}
            }
            if(event.type==KeyPress&&event.xkey.window==win&&active_page==0){
                KeySym key=XLookupKeysym(&event.xkey,0);
                if(key==XK_Tab||key==XK_Down||key==XK_Up||key==XK_ISO_Left_Tab){
                    focus_card=(focus_card+((key==XK_Up||key==XK_ISO_Left_Tab)?2:1))%3;needs_redraw=1;
                }
                else if(key==XK_Return||key==XK_KP_Enter||key==XK_space){
                    if(focus_card==0)open_program("Sorter");
                    else if(focus_card==1)open_program("Sorter.Config");
                    else su_launch(0);
                }
                else if(key==XK_Escape)running=0;
                else if(key==XK_1)open_program("Sorter");
                else if(key==XK_2)open_program("Sorter.Config");
                else if(key==XK_3)su_launch(0);
            }
        }
        child_exited_impl(&sorter_child,"Sorter process exited.");
        child_exited_impl(&config_child,"Config editor exited.");
        if((active_page==1 && sorter_child<0) || (active_page==2 && config_child<0)){
            show_page(0);
            draw_status("The page closed. Main menu is ready.");
        }
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
    su_cleanup();XFreeCursor(dpy,hand_cursor);XFreeGC(dpy,gc);XDestroyWindow(dpy,win);XCloseDisplay(dpy);return 0;
}
