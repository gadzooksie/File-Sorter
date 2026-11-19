#ifndef FILE_SORTER_MENU_BRIDGE_H
#define FILE_SORTER_MENU_BRIDGE_H
/* X11 bridge from Sorter / Config back to the persistent launcher window. */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
static Window fs_menu_launcher=None;
static void fs_menu_register(Display *display, Window child, const char *slot){
    const char *raw=getenv("FILE_SORTER_LAUNCHER_XID");
    if(!raw || !*raw)return;
    errno=0;char *end=NULL;unsigned long val=strtoul(raw,&end,0);
    if(errno || !end || *end || val==0)return;
    fs_menu_launcher=(Window)val;
    Atom prop=XInternAtom(display,slot,False);
    unsigned long child_id=(unsigned long)child;
    XChangeProperty(display,fs_menu_launcher,prop,XA_WINDOW,32,PropModeReplace,(unsigned char*)&child_id,1);
    XFlush(display);
}
static int fs_menu_show(Display *display, Window child){
    if(fs_menu_launcher!=None){
        XMapRaised(display,fs_menu_launcher);
        /* Hide without closing the process. XMapRaised in the launcher restores
           the same window, preserving sorter state and its worker process. */
        XUnmapWindow(display,child);
        XFlush(display);
        return 1;
    }
    /* A directly launched --sorter/--config process has no parent menu.
       Do not hide it or spawn an untracked menu that cannot restore it. */
    return 0;
}
#endif
